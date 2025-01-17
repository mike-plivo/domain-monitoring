from base_monitor import BaseMonitor, MonitorFactory
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
        if not self.domain:
            raise ValueError("domain is required")
        self.whois_timeout = whois_timeout
        self.WHOIS_SERVERS = WHOIS_SERVERS
        if not whois_server or whois_server == "auto":
            self.whois_server = self._get_whois_server()
        else:
            self.whois_server = whois_server
        BaseMonitor.__init__(self, slack_webhook_url=slack_webhook_url, domain=domain, whois_server=self.whois_server)
        self.logger.info(f"using WHOIS server {self.whois_server}")

    def _get_whois_server(self):
        """ Find WHOIS server for the given domain. """
        for tld, server in self.WHOIS_SERVERS.items():
            suffix = '.' + tld
            suffix = suffix.lower().strip()
            domain_suffix = self.domain.split('.', 1)[-1]
            if domain_suffix == suffix:
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
                raise Exception("no WHOIS server found")

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
            raise e

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


class WHOISMonitorFactory(MonitorFactory):
    def __init__(self, monitor_class=WHOISMonitor):
        MonitorFactory.__init__(self, monitor_class)

    def serve_forever(self):
        self.parser.add_argument('--domain', type=str, help='Domain to monitor', default=None, required=True)
        self.parser.add_argument("--whois_server", help="whois_server (default autodetected).", default=None)
        self.parser.add_argument("--whois_timeout", type=int, help="whois_timeout (default 30 seconds).", default=30)
        self.parser.add_argument("--slack_webhook_url", help="slack webhook url (default disabled)", default=None)
        self.parser.add_argument("--pause", help="pause time in seconds (default 60) between each check", type=int, default=300)
        self.args = self.parser.parse_args()
        self.slack_webhook_url = self.args.slack_webhook_url
        self.pause = self.args.pause
        self.monitor = self.monitor_class(self.args.domain, whois_server=self.args.whois_server, whois_timeout=self.args.whois_timeout, 
                                          slack_webhook_url=self.slack_webhook_url)
        self.monitor.serve_forever(pause=self.pause)
        return self.monitor

if __name__ == "__main__":
    WHOISMonitorFactory(WHOISMonitor).serve_forever()
