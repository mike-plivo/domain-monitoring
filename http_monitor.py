from base_monitor import BaseMonitor, MonitorFactory
import requests

class HTTPMonitor(BaseMonitor):
    def __init__(self, url, method='GET', payload=None, headers=None, 
                 connect_timeout=5, timeout=15, 
                 verify_ssl=True,
                 slack_webhook_url=None):
        self.url = url
        if not self.url:
            raise ValueError("url is required")
        self.method = method
        self.connect_timeout = connect_timeout
        self.timeout = timeout
        self.payload = payload
        self.headers = headers
        self.verify_ssl = verify_ssl
        BaseMonitor.__init__(self, slack_webhook_url=slack_webhook_url, url=url, method=method)

    def fetch_new_records(self):
        records = {}
        self.logger.debug(f"fetching {self.method} {self.url}")
        try:
            response = requests.request(self.method, self.url, 
                                        data=self.payload, 
                                        headers=self.headers, 
                                        verify=self.verify_ssl,
                                        timeout=(self.connect_timeout, self.timeout))
            response.raise_for_status()
            records[self.url] = {'method': self.method, 
                                 'payload': self.payload,
                                 'headers': self.headers,
                                 'timeout': self.timeout,
                                 'verify_ssl': self.verify_ssl,
                                 'connect_timeout': self.connect_timeout,
                                 'response_status_code': response.status_code, 
                                 'response_text': response.text}
            self.logger.debug(f"fetched url: {records}")
            return records
        except Exception as e:  
            self.logger.error(f"could not fetch url: {e}", exc_info=True)
            raise e


class HTTPMonitorFactory(MonitorFactory):
    def __init__(self, monitor_class=HTTPMonitor):
        MonitorFactory.__init__(self, monitor_class)

    def serve_forever(self):
        self.parser.add_argument('--url', type=str, help='URL to monitor', default=None, required=True)
        self.parser.add_argument("--method", help="HTTP method (GET or POST, default GET)", default='GET')
        self.parser.add_argument("--payload", help="HTTP payload (default None)", default=None)
        self.parser.add_argument("--headers", help="HTTP headers (default None)", default=None)
        self.parser.add_argument("--connect_timeout", type=int, help="HTTP connect timeout (default 5 seconds)", default=5)
        self.parser.add_argument("--timeout", type=int, help="HTTP timeout (default 15 seconds)", default=15)
        self.parser.add_argument("--verify_ssl", type=bool, help="verify SSL (default True)", default=True)
        self.parser.add_argument("--slack_webhook_url", help="slack webhook url (default disabled)", default=None)
        self.parser.add_argument("--pause", help="pause time in seconds (default 60) between each check", type=int, default=60)
        self.args = self.parser.parse_args()
        self.slack_webhook_url = self.args.slack_webhook_url
        self.pause = self.args.pause
        self.monitor = self.monitor_class(self.args.url, method=self.args.method, payload=self.args.payload, headers=self.args.headers,
                                        connect_timeout=self.args.connect_timeout, timeout=self.args.timeout, verify_ssl=self.args.verify_ssl,
                                        slack_webhook_url=self.slack_webhook_url)
        self.monitor.serve_forever(pause=self.pause)
        return self.monitor

if __name__ == "__main__":
    HTTPMonitorFactory(HTTPMonitor).serve_forever()

