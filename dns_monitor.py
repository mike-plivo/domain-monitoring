import dns.resolver
import json
import logging
import argparse
import redis
from utils import slack

class DNSMonitor:
    def __init__(self, domain, resolvers, slack_webhook_url=None,
                 redis_client=None):
        self.domain = domain
        self.resolver = dns.resolver.Resolver()
        self.resolver.nameservers = list(set([ x.strip() for x in resolvers.split(',') ]))
        self.slack_webhook_url = slack_webhook_url
        if redis_client is None:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        else:
            self.redis_client = redis_client
        self.redis_key = f"dns_records:{self.domain}"
        self.logger = logging.getLogger("DNSMonitor")
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        fh = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        ch.setFormatter(fh)
        self.logger.addHandler(ch)

    def fetch_dns_records(self):
        records = {}
        for record_type in ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA']:
            try:
                answers = self.resolver.resolve(self.domain, record_type)
                records[record_type] = [str(rdata) for rdata in answers]
            except dns.resolver.NoAnswer as ne:
                self.logger.warning(f"skipping {record_type}: {ne}")
            except Exception as e:
                self.logger.warning(f"skipping {record_type}: could not fetch record: {e}", exc_info=True)
        return records

    def store_records_in_redis(self, records):
        self.redis_client.set(self.redis_key, json.dumps(records))

    def detect_changes(self, new_records):
        changes = []
        cached_records = self.redis_client.get(self.redis_key)
        if not cached_records:
            self.logger.info("DNS records not cached yet, nothing to compare with.")
            changes.append("DNS records not cached yet, nothing to compare with.")
            for k, v in new_records.items():
                changes.append(f"- {k}: {v}")
        else:
            cached_records = json.loads(cached_records)
            self.logger.debug(f"cached records: {cached_records}")
            self.logger.debug(f"new records: {new_records}")
            for k, v in cached_records.items():
                if k not in new_records:
                    self.logger.info(f"{k} record: changed from: {v} -> to: None (missing)")
                    changes.append(f"- {k} record: changed from: {v} -> to: None (missing)")
                if k in new_records and sorted(new_records[k]) != sorted(v):
                    self.logger.info(f"{k} record: changed from: {v} -> to: {new_records[k]}")
                    changes.append(f"- {k} record: changed from: {v} -> to: {new_records[k]}")
        if len(changes) > 0:
            self.logger.debug(f"caching new records")
            self.store_records_in_redis(new_records)
        else:
            self.logger.debug(f"no changes detected, not caching records")
        return changes

    def monitor(self):
        """ Monitor the specified domain for WHOIS data changes. """
        self.logger.info(f"{self.domain}: monitoring started with resolver {self.resolver.nameservers}")
        self.logger.info(f"fetching DNS records with resolver {self.resolver.nameservers}")
        dns_records = self.fetch_dns_records()
        self.logger.info(f"found new records: {json.dumps(dns_records)}")
        changed_data = self.detect_changes(dns_records)
        if changed_data and len(changed_data) > 0:
            if self.slack_webhook_url:
                slack_message = f"DNSMonitor {self.domain}: changes found\n"
                slack_message += "\n".join(changed_data)
                slack(slack_message, self.slack_webhook_url)
        else:
            self.logger.debug("no changes")
        self.logger.info(f"{self.domain}: monitoring completed")

def cli():
    parser = argparse.ArgumentParser(description='DNS Resolver Script')
    parser.add_argument('--domain', type=str, help='Domain to resolve')
    parser.add_argument('--resolvers', type=str, help='DNS resolvers addresses (comma separated list)', default='8.8.8.8')
    parser.add_argument("--slack_webhook_url", help="slack webhook url (default disabled)", default=None)
    args = parser.parse_args()
    domain = args.domain
    resolvers = args.resolvers
    slack_webhook_url = args.slack_webhook_url
    DNSMonitor(domain, resolvers, slack_webhook_url).monitor()


if __name__ == "__main__":
    cli()

