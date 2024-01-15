import logging
import argparse
import json
import dns.resolver
from utils import slack, create_logger, create_redis_client, get_region, get_sensor_id

class DNSRecordMonitor:
    def __init__(self, domain, resolvers, slack_webhook_url=None):
        self.domain = domain
        self.sensor_id = get_sensor_id()
        self.region = get_region()
        self.prefix = f"[DNSRecordMonitor][id={self.sensor_id}][geo={self.region}][domain={self.domain}]"
        self.resolver = dns.resolver.Resolver()
        self.resolver.nameservers = list(set([ x.strip() for x in resolvers.split(',') ]))
        self.slack_webhook_url = slack_webhook_url
        self.redis_client = create_redis_client()
        self.redis_key = f'dns_record_monitor:{self.sensor_id}:{self.domain}'
        self.logger = create_logger(self.prefix)

    def _fetch_dns_records(self):
        records = {}
        self.logger.debug(f"fetching DNS records for {self.domain} using resolvers {self.resolver.nameservers}")
        for record_type in ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA']:
            try:
                answers = self.resolver.resolve(self.domain, record_type)
                records[record_type] = [str(rdata) for rdata in answers]
            except dns.resolver.NoAnswer as ne:
                self.logger.warning(f"skipping {record_type}: {ne}")
            except Exception as e:
                self.logger.warning(f"skipping {record_type}: could not fetch record: {e}", exc_info=True)
        return records

    def _store_records_in_redis(self, records):
        self.redis_client.set(self.redis_key, json.dumps(records))
        self.redis_client.expire(self.redis_key, 86400)

    def _refresh_ttl(self):
        try:
            self.redis_client.expire(self.redis_key, 86400)
        except Exception as e:
            self.logger.warning(f"could not refresh Redis TTL: {e}", exc_info=True)

    def _get_cached_records(self):
        return self.redis_client.get(self.redis_key)

    def detect_changes(self):
        new_records = self._fetch_dns_records()
        self.logger.info(f"found new records: {json.dumps(new_records)}")
        changed = False
        changes = set()
        cached_records = self._get_cached_records()
        if not cached_records:
            msg = "DNS records are not cached yet, nothing to compare with."
            self.logger.info(msg)
            for k, v in new_records.items():
                changes.add(f"{k}: {v}")
            changes = list(changes)
            self.logger.debug(f"caching DNS records")
            self._store_records_in_redis(new_records)
            return changed, msg, list(changes)

        cached_records = json.loads(cached_records)
        self.logger.debug(f"cached records: {cached_records}")
        self.logger.debug(f"new records: {new_records}")
        for k, v in cached_records.items():
            if k not in new_records:
                self.logger.info(f"{k} -> record deleted: {v} -> (not present)")
                changes.add(f"{k} -> record deleted: {v} -> (not present)")
            elif k in new_records and sorted(new_records[k]) != sorted(v):
                self.logger.info(f"{k} -> record changed: {v} -> {new_records[k]}")
                changes.add(f"{k} -> record changed: {v} -> {new_records[k]}")
        for k, v in new_records.items():
            if k not in cached_records:
                self.logger.info(f"{k} -> record added: (not present) -> {v}")
                changes.add(f"{k} -> record added: (not present) -> {v}")
            elif k in cached_records and sorted(cached_records[k]) != sorted(v):
                self.logger.info(f"{k} -> record changed: {cached_records[k]} -> {v}")
                changes.add(f"{k} -> record changed: {cached_records[k]} -> {v}")
        if len(changes) > 0:
            msg = "DNS records changed"
            changed = True
            self.logger.info(msg)
            self.logger.debug(f"caching new DNS records")
            self._store_records_in_redis(new_records)
        else:
            msg = "DNS records not changed"
            changed = False
            self.logger.info(msg)
            self._refresh_ttl()
        return changed, msg, list(changes)

    def monitor(self):
        """ Monitor the specified domain for WHOIS data changes. """
        self.logger.info(f"monitoring started")
        self.logger.info(f"fetching DNS records with resolver {self.resolver.nameservers}")
        changed, msg, changed_data = self.detect_changes()
        if changed_data and len(changed_data) > 0:
            if self.slack_webhook_url:
                if changed is True: emoji = ":warning:"
                else: emoji = ":information_source:"
                slack_message = f"{emoji} *{self.prefix}*\n{msg}\n"
                slack_message += '```'
                for data in changed_data:
                    slack_message += f"- {data}\n"
                slack_message += '```'
                slack(slack_message, self.slack_webhook_url)
        elif changed is True and len(changed_data) == 0:
            if self.slack_webhook_url:
                slack_message = f":warning: *{self.prefix}*\n{msg}\n"
                slack(slack_message, self.slack_webhook_url)
        else:
            self.logger.debug("no changes")
        self.logger.info(f"monitoring completed")

def cli():
    parser = argparse.ArgumentParser(description='DNS Resolver Script')
    parser.add_argument('--domains', type=str, help='Domains to monitor (comma separated list)', default=None)
    parser.add_argument('--resolvers', type=str, help='DNS resolvers addresses (comma separated list)', default='8.8.8.8')
    parser.add_argument("--slack_webhook_url", help="slack webhook url (default disabled)", default=None)
    args = parser.parse_args()
    domains = list(set([ x.strip() for x in args.domains.split(',') ]))
    resolvers = args.resolvers
    slack_webhook_url = args.slack_webhook_url
    for domain in domains:
        DNSRecordMonitor(domain, resolvers, slack_webhook_url).monitor()


if __name__ == "__main__":
    cli()

