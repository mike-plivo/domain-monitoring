from base_monitor import BaseMonitor
import dns.resolver

class DNSRecordMonitor(BaseMonitor):
    def __init__(self, domain, resolvers=None, record_types=None, slack_webhook_url=None):
        BaseMonitor.__init__(self, slack_webhook_url=slack_webhook_url, domain=domain, resolvers=resolvers)
        self.domain = domain
        if not record_types or record_types == 'auto':
            record_types = 'A,AAAA,MX,NS,TXT,CNAME,SOA'
        if not resolvers or resolvers == 'auto':
            resolvers = '208.67.222.222,208.67.220.220'
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

def cli():
    import argparse
    parser = argparse.ArgumentParser(description='DNS Resolver Script')
    parser.add_argument('--domain', type=str, help='Domain to monitor', default=None)
    parser.add_argument('--resolvers', type=str, help="DNS resolvers addresses (comma separated list). Default 208.67.222.222,208.67.220.220.", default=None)
    parser.add_argument("--record_types", help="DNS record types to monitor (comma separated list). Default A,AAAA,MX,NS,TXT,CNAME,SOA.", default=None)
    parser.add_argument("--slack_webhook_url", help="slack webhook url (default disabled).", default=None)
    parser.add_argument("--pause", help="pause time in seconds (default 60) between each check.", type=int, default=60)
    args = parser.parse_args()
    domain = args.domain
    resolvers = args.resolvers
    slack_webhook_url = args.slack_webhook_url
    DNSRecordMonitor(domain, resolvers, slack_webhook_url).serve_forever(pause=args.pause)


if __name__ == "__main__":
    cli()

