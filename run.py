import subprocess
import time
import argparse


class Runner(object):
    WHOIS_SCRIPT = 'whois_monitor.py'
    DNS_SCRIPT = 'dns_monitor.py'

    def __init__(self):
        self.processes = []
        self.parse_options()

    def parse_options(self):
        parser = argparse.ArgumentParser(description="Command line argument parser")
        # Adding the --whois argument
        parser.add_argument('--whois', action='append', nargs=3, metavar=('DOMAIN', 'SERVER', 'TIMEOUT'),
                            help='Information for WHOIS query. Can be specified multiple times.')
        # Adding the --dns argument
        parser.add_argument('--dns', action='append', nargs=3, metavar=('DOMAIN', 'RESOLVERS', 'RECORD_TYPES'),
                            help='Information for DNS query.\nDOMAIN: the domain to monitor\nRESOLVERS: the resolvers to use or \'auto\'.Can be specified multiple times.')
        parser.add_argument("--slack_webhook_url", help="Slack webhook url (default disabled).", default='')
        parser.add_argument('--python_path', help='Path to python executable', default='python3')
        parser.add_argument('--whois_script', help='Path to whois script', default=self.WHOIS_SCRIPT)
        parser.add_argument('--dns_script', help='Path to dns script', default=self.DNS_SCRIPT)
        self.args = parser.parse_args()
        self.python_path = self.args.python_path or 'python3'
        self.whois_script = self.args.whois_script or self.WHOIS_SCRIPT
        self.dns_script = self.args.dns_script or self.DNS_SCRIPT

    def add_whois_command(self, domain, server, timeout=300):
        # Run the whois script
        self.processes.append(subprocess.Popen([self.python_path, self.whois_script, 
                                                "--domain", domain, "--whois_server", server, "--whois_timeout", timeout,
                                                "--slack_webhook_url", self.args.slack_webhook_url
                                                ]))

    def add_dns_command(self, domain, resolvers, record_types):
        # Run the dns script
        self.processes.append(subprocess.Popen([self.python_path, self.dns_script, 
                                                "--domain", domain, "--resolvers", resolvers, "--record_types", record_types,
                                                "--slack_webhook_url", self.args.slack_webhook_url
                                                ]))

    def serve_forever(self):
        for whois in self.args.whois:
            self.add_whois_command(whois[0], whois[1], whois[2])
            time.sleep(0.2)
        for dns in self.args.dns:
            self.add_dns_command(dns[0], dns[1], dns[2])
            time.sleep(0.2)
        for process in self.processes:
            process.wait()

if __name__ == '__main__':
    Runner().serve_forever()

