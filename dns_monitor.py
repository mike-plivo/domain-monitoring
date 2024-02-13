from base_monitor import BaseMonitor, MonitorFactory
import dns.resolver

class DNSRecordMonitor(BaseMonitor):
    def __init__(self, domain, resolvers=None, record_types=None, slack_webhook_url=None):
        if not resolvers or resolvers == 'auto':
            resolvers = '208.67.222.222,208.67.220.220'
        if not record_types or record_types == 'auto':
            record_types = 'A,AAAA,MX,NS,TXT,CNAME,SOA'
        BaseMonitor.__init__(self, slack_webhook_url=slack_webhook_url, domain=domain, resolvers=resolvers)
        self.domain = domain
        if not self.domain:
            raise ValueError("domain is required")
        self.resolver = dns.resolver.Resolver()
        self.resolver.nameservers = list(set([ x.strip() for x in resolvers.split(',') ]))
        self.record_types = list(set([ x.strip() for x in record_types.split(',') ]))

    def fetch_new_records(self):
        records = {}
        self.logger.debug(f"fetching DNS records for {self.domain} using resolvers {self.resolver.nameservers}")
        for record_type in self.record_types:
            try:
                self.logger.debug(f"fetching {record_type} records")
                answers = self.resolver.resolve(self.domain, record_type)
                records[record_type] = [str(rdata) for rdata in answers]
            except dns.resolver.NoAnswer as ne:
                self.logger.warning(f"skipping {record_type}: {ne}")
            except Exception as e:
                self.logger.warning(f"skipping {record_type}: could not fetch record: {e}", exc_info=True)
        return records

class DNSMonitorFactory(MonitorFactory):
    def __init__(self, monitor_class=DNSRecordMonitor):
        MonitorFactory.__init__(self, monitor_class)

    def serve_forever(self):
        self.parser.add_argument('--domain', type=str, help='Domain to monitor', default=None, required=True)
        self.parser.add_argument('--resolvers', type=str, help="DNS resolvers addresses (comma separated list). Default 208.67.222.222,208.67.220.220.", default=None)
        self.parser.add_argument("--record_types", help="DNS record types to monitor (comma separated list). Default A,AAAA,MX,NS,TXT,CNAME,SOA.", default=None)
        self.parser.add_argument("--slack_webhook_url", help="slack webhook url (default disabled)", default=None)
        self.parser.add_argument("--pause", help="pause time in seconds (default 60) between each check", type=int, default=60)
        self.args = self.parser.parse_args()
        self.slack_webhook_url = self.args.slack_webhook_url
        self.pause = self.args.pause
        self.monitor = self.monitor_class(self.args.domain, self.args.resolvers, self.args.record_types, self.slack_webhook_url)
        self.monitor.serve_forever(pause=self.pause)
        return self.monitor

if __name__ == "__main__":
    DNSMonitorFactory(DNSRecordMonitor).serve_forever()

