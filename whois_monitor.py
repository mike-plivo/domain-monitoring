import logging
import whois21
import json
from whois_servers import WHOIS_SERVERS
from utils import slack, create_logger, create_redis_client, get_region, get_sensor_id

# avoid urllib3 debug logs
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("urllib3").propagate = False



class WHOISMonitor(object):
    """ Monitor a given domain. """
    WHOIS_FIELDS = [
        'DOMAIN NAME',
        'REGISTRY DOMAIN ID',
        'REGISTRAR WHOIS SERVER',
        'REGISTRAR URL',
        'UPDATED DATE',
        'CREATION DATE',
        'REGISTRY EXPIRY DATE',
        'REGISTRAR',
        'REGISTRAR IANA ID',
        'REGISTRAR ABUSE CONTACT EMAIL',
        'REGISTRAR ABUSE CONTACT PHONE',
        'DOMAIN STATUS',
        'NAME SERVER',
        'DNSSEC']

    def __init__(self, domain, whois_server=None, whois_timeout=30, 
                 slack_webhook_url=None, redis_client=None):
        self.domain = domain.lower().strip()
        self.region = get_region()
        self.sensor_id = get_sensor_id()
        self.prefix = f"[WHOISMonitor][id={self.sensor_id}][geo={self.region}][domain={self.domain}]"
        self.whois_server = whois_server
        self.whois_timeout = whois_timeout
        self.slack_webhook_url = slack_webhook_url
        self.redis_client = create_redis_client()
        self.redis_key = f'whois_monitor:{self.sensor_id}:{self.domain}'
        self.logger = create_logger(self.prefix)
        self.WHOIS_SERVERS = WHOIS_SERVERS

    def _get_whois_server(self):
        """ Find WHOIS server for the given domain. """
        if self.whois_server:
            return self.whois_server
        for tld, server in self.WHOIS_SERVERS.items():
            suffix = '.' + tld
            suffix = suffix.lower().strip()
            if self.domain[len(suffix)+1:] == suffix:
                self.logger.debug(f"found WHOIS server {server} for {suffix}")
                self.whois_server = server
                return self.whois_server
        return None

    def _whois_strip_data(self, data):
        """ Extract WHOIS fields from WHOIS data. """
        if not data:
            return {}
        fields = {}
        for k, v in data.items():
            if k in self.WHOIS_FIELDS:
                fields[k] = v
        return fields

    def _fetch_whois_data(self):
        """ Fetch the given domain. """
        try:
            whois_server = self._get_whois_server()
            if whois_server is None:
                msg = f"Error fetching {self.domain}: no WHOIS server found"
                self.logger.error(msg)
                return msg, None
            self.logger.info(f"fetching WHOIS data from {whois_server}")
            result = whois21.WHOIS(self.domain, servers=[whois_server], 
                                   use_rdap=False, timeout=self.whois_timeout)
            if result.success is False:
                msg = f"Error fetching {self.domain}: {result.error}"
                self.logger.error(msg)
                return msg, None
            data = self._whois_strip_data(result.whois_data)
            self.logger.debug(f"fetched {data}")
            msg = f"WHOIS data fetched for {self.domain}"
            return msg, data
        except Exception as e:
            msg = f"Error fetching {self.domain}: {e}"
            self.logger.error(msg)
            return msg, None

    def _store_whois_data(self, data):
        """ Store WHOIS data in Redis. """
        self.redis_client.set(self.redis_key, json.dumps(data))
        self.redis_client.expire(self.redis_key, 86400)

    def _refresh_ttl(self):
        try:
            self.redis_client.expire(self.redis_key, 86400)
        except Exception as e:
            self.logger.warning(f"could not refresh Redis TTL: {e}", exc_info=True)

    def _get_cached_whois_data(self):
        """ Retrieve cached WHOIS data from Redis. """
        data = self.redis_client.get(self.redis_key)
        if data is None or len(data) == 0:
            return None
        data = self._whois_strip_data(json.loads(data))
        if not data:
            return None
        self.logger.debug(f"cached {data}")
        return data

    def detect_changes(self):
        """ Check if WHOIS data has changed compared to cached data. """
        chnaged = False
        changes = set()
        msg, current_data = self._fetch_whois_data()

        if current_data is None:
            changed = True
            return changed, msg, list(changes)

        cached_data = self._get_cached_whois_data()
        if cached_data is None:
            changed = False
            msg = f"WHOIS records are not cached yet, nothing to compare with."
            self.logger.info(msg)
            for k, v in current_data.items():
                changes.add(f"{k}: {v}")
            changes = list(changes)
            self.logger.debug(f"caching WHOIS records")
            self._store_whois_data(current_data)
            return changed, msg, list(changes)

        for cached_key, cached_value in cached_data.items():
            current_value = current_data.get(cached_key, None)
            if current_value is None:
                changes.add(f"{cached_key} -> record deleted: {cached_value} -> (not present)")
                self.logger.info(f"{cached_key} -> record deleted: {cached_value} -> (not present)")
            elif cached_value != current_value:
                changes.add(f"{cached_key} -> record changed: {cached_value} -> {current_value}")
                self.logger.info(f"{cached_key} -> record changed: {cached_value} -> {current_value}")
        for current_key, current_value in current_data.items():
            cached_value = cached_data.get(current_key, None)
            if cached_value is None:
                changes.add(f"{current_key} -> record added: (not present) -> {current_value}")
                self.logger.info(f"{current_key} -> record added: (not present) -> {current_value}")
            elif cached_value != current_value:
                changes.add(f"{current_key} -> record changed: {cached_value} -> {current_value}")
                self.logger.info(f"{current_key} -> record changed: {cached_value} -> {current_value}")
        if len(changes) > 0:
            changed = True
            msg = f"WHOIS records changed"
            self.logger.info(msg)
            self.logger.debug(f"caching new WHOIS records")
            self._store_whois_data(current_data)
        else:
            msg = f"WHOIS records not changed"
            changed = False
            self.logger.info(msg)
            self._refresh_ttl()
        return changed, msg, list(changes)

    def monitor(self):
        """ Monitor the specified domain for WHOIS data changes. """
        self.logger.info(f"monitoring started")
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
    import argparse
    parser = argparse.ArgumentParser(description="WHOIS monitor")
    parser.add_argument("--domain", help="domain to monitor")
    parser.add_argument("--slack_webhook_url", help="slack webhook url (default disabled)", default=None)
    parser.add_argument("--whois_server", help="whois_server (default autodetected)", default=None)
    parser.add_argument("--whois_timeout", type=int, help="whois_timeout (default 30 seconds)", default=30)
    args = parser.parse_args()
    domain = args.domain
    whois_server = args.whois_server
    whois_timeout = args.whois_timeout
    slack_webhook_url = args.slack_webhook_url
    WHOISMonitor(domain, whois_server=whois_server, whois_timeout=whois_timeout, 
                 slack_webhook_url=slack_webhook_url).monitor()

if __name__ == "__main__":
    cli()
