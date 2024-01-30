from base_monitor import BaseMonitor
import whois21
import json
from whois_servers import WHOIS_SERVERS
# avoid urllib3 debug logs
import logging
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("urllib3").propagate = False



class WHOISMonitor(BaseMonitor):
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
                 slack_webhook_url=None):
        self.domain = domain.lower().strip()
        if whois_server:
            self.whois_server = whois_server
        else:
            self.whois_server = self._get_whois_server()
        self.whois_timeout = whois_timeout
        self.WHOIS_SERVERS = WHOIS_SERVERS
        BaseMonitor.__init__(self, slack_webhook_url=slack_webhook_url, domain=domain, whois_server=self.whois_server)

    def _get_whois_server(self):
        """ Find WHOIS server for the given domain. """
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

    def fetch_new_records(self):
        """ Fetch the given domain. """
        try:
            if self.whois_server is None:
                msg = f"Error fetching {self.domain}: no WHOIS server found"
                self.logger.error(msg)
                return {}
            self.logger.info(f"fetching WHOIS data from {self.whois_server}")
            result = whois21.WHOIS(self.domain, servers=[self.whois_server], 
                                   use_rdap=False, timeout=self.whois_timeout)
            if result.success is False:
                msg = f"Error fetching {self.domain}: {result.error}"
                self.logger.error(msg)
                return {}
            data = self._whois_strip_data(result.whois_data)
            self.logger.debug(f"fetched {data}")
            return data
        except Exception as e:
            msg = f"Error fetching {self.domain}: {e}"
            self.logger.error(msg)
            return {}

    def get_cached_records(self):
        """ Retrieve cached WHOIS data from Redis. """
        data = self.redis_client.get(self.redis_key)
        if data is None or len(data) == 0:
            return json.dumps({})
        data = self._whois_strip_data(json.loads(data))
        if not data:
            return json.dumps({})
        self.logger.debug(f"cached {data}")
        return json.dumps(data)

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="WHOIS monitor")
    parser.add_argument("--domain", help="domain to monitor")
    parser.add_argument("--slack_webhook_url", help="slack webhook url (default disabled)", default=None)
    parser.add_argument("--whois_server", help="whois_server (default autodetected)", default=None)
    parser.add_argument("--whois_timeout", type=int, help="whois_timeout (default 30 seconds)", default=30)
    parser.add_argument("--pause", help="pause time in seconds (default 300) between each check", type=int, default=300)
    args = parser.parse_args()
    domain = args.domain
    whois_server = args.whois_server
    whois_timeout = args.whois_timeout
    slack_webhook_url = args.slack_webhook_url
    WHOISMonitor(domain, whois_server=whois_server, whois_timeout=whois_timeout, 
                 slack_webhook_url=slack_webhook_url).serve_forever(pause=args.pause)


if __name__ == "__main__":
    cli()
