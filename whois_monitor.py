import logging
import whois21
import json
from whois_servers import WHOIS_SERVERS
from utils import slack, create_logger, create_redis_client, get_region

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
        self.whois_server = whois_server
        self.whois_timeout = whois_timeout
        self.slack_webhook_url = slack_webhook_url
        self.redis_client = create_redis_client()
        self.redis_key = f"whois_records:{self.domain}"
        self.logger = create_logger(f"WHOISMonitor-{self.domain}")
        self.WHOIS_SERVERS = WHOIS_SERVERS

    def _get_whois_server(self):
        """ Find WHOIS server for the given domain. """
        if self.whois_server:
            return self.whois_server
        for tld, server in self.WHOIS_SERVERS.items():
            suffix = '.' + tld
            suffix = suffix.lower().strip()
            if self.domain[len(suffix)+1:] == suffix:
                self.logger.debug(f"{self.domain}: found WHOIS server {server} for {suffix}")
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
                self.logger.error(f"Error fetching {self.domain}: no WHOIS server found")
                return None
            self.logger.info(f"fetching WHOIS data from {whois_server}")
            result = whois21.WHOIS(self.domain, servers=[whois_server], 
                                   use_rdap=False, timeout=self.whois_timeout)
            if result.success is False:
                self.logger.error(f"Error fetching {self.domain}: {result.error}")
                return None
            data = self._whois_strip_data(result.whois_data)
            self.logger.debug(f"fetched {data}")
            return data
        except Exception as e:
            self.logger.error(f"Error fetching {self.domain}: {e}")
            return None

    def _store_whois_data(self, data):
        """ Store WHOIS data in Redis. """
        self.redis_client.set(self.redis_key, json.dumps(data))

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

    def _whois_monitor(self):
        """ Check if WHOIS data has changed compared to cached data. """
        changed_data = set()
        current_data = self._fetch_whois_data()

        if current_data is None:
            return list(changed_data)

        cached_data = self._get_cached_whois_data()
        if cached_data is None:
            self.logger.info(f"WHOIS data not cached yet, nothing to compare with.")
            self._store_whois_data(current_data)
            if self.slack_webhook_url is not None:
                slack_message = f"[WHOISMonitor {get_region()}] {self.domain}: changes found\n"
                slack_message += f"WHOIS data not cached yet, nothing to compare with.\n"
                for k, v in current_data.items():
                    slack_message += f"- {k}: {v}\n"
                slack(slack_message, self.slack_webhook_url)
            return list(changed_data)

        for cached_key, cached_value in cached_data.items():
            current_value = current_data.get(cached_key, None)
            if current_value is None:
                changed_data.add(f"{cached_key}: changed from: {cached_value} -> to: None (missing)")
                self.logger.info(f"{cached_key}: changed from: {cached_value} -> to: None (missing)")
            if cached_value != current_value:
                changed_data.add(f"{cached_key}: changed from: {cached_value} -> to: {current_value}")
                self.logger.info(f"{cached_key}: changed from: {cached_value} -> to: {current_value}")
        for current_key, current_value in current_data.items():
            cached_value = cached_data.get(current_key, None)
            if cached_value is None:
                changed_data.add(f"{current_key}: changed from: None (not present) -> to: {current_value}")
                self.logger.info(f"{current_key}: changed from: None (not present) -> to: {current_value}")
            if cached_value != current_value:
                changed_data.add(f"{current_key}: changed from: {cached_value} -> to: {current_value}")
                self.logger.info(f"{current_key}: changed from: {cached_value} -> to: {current_value}")

        if len(changed_data) > 0:
            self.logger.info(f"changes found")
            self._store_whois_data(current_data)
            if self.slack_webhook_url is not None:
                slack_message = f"[WHOISMonitor {get_region()}] {self.domain}: changes found\n"
                for data in changed_data:
                    slack_message += f"- {data}\n"
                slack(slack_message, self.slack_webhook_url)
        else:
            self.logger.info(f"no changes")
        return list(changed_data)

    def monitor(self):
        """ Monitor the specified domain for WHOIS data changes. """
        self.logger.info(f"{self.domain}: monitoring started")
        self._whois_monitor()
        self.logger.info(f"{self.domain}: monitoring completed")

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
