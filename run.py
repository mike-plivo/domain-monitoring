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
        parser.add_argument('--whois', action='append',
                            help='Information for WHOIS query. Can be specified multiple times. Format: --whois=\'domain=<DOMAIN>;server=<OPTIONAL>;timeout=<OPTIONAL>;pause=<OPTIONAL>\'. Default WHOIS server is selected if not specified. Default WHOIS query timeout is 30 seconds. Default pause between each query is 300 seconds.')
        # Adding the --dns argument
        parser.add_argument('--dns', action='append', 
                            help='Information for DNS query. Can be specified multiple times. Format: --dns=\'domain=<DOMAIN>;resolvers=<OPTIONAL>;record_types=<OPTIONAL>;pause=<OPTIONAL>\'. Default resolvers are used if not specified (208.67.222.222,208.67.220.220). Default record types are A,AAAA,MX,NS,TXT,CNAME,SOA. Default pause between each query is 60 seconds.')

        parser.add_argument("--slack_webhook_url", help="Slack webhook url (default disabled).", default='')
        parser.add_argument('--python_exe', help='Path to python executable', default='python3')
        parser.add_argument('--whois_script', help='Path to whois script', default=self.WHOIS_SCRIPT)
        parser.add_argument('--dns_script', help='Path to dns script', default=self.DNS_SCRIPT)

        self.args = parser.parse_args()
        self.python_exe = self.args.python_exe or 'python3'
        self.whois_script = self.args.whois_script or self.WHOIS_SCRIPT
        self.dns_script = self.args.dns_script or self.DNS_SCRIPT

    def spawn_whois_command(self, args):
        # args format is domain=<domain>;server=<optional>;timeout=30
        args = args.strip("'")
        args = args.strip('"')
        options = args.split(';')
        domain = ''
        server = ''
        timeout = '30'
        pause = '300'
        for option in options:
            key, value = option.split('=')
            key = key.strip()
            value = value.strip()
            if key == 'domain':
                domain = value
            elif key == 'server':
                server = value
            elif key == 'timeout':
                timeout = value
            elif key == 'pause':
                pause = value
        # Run the whois script
        self.processes.append(subprocess.Popen([self.python_exe, self.whois_script, 
                                                "--domain", domain, "--whois_server", server, "--whois_timeout", timeout,
                                                "--slack_webhook_url", self.args.slack_webhook_url,
                                                "--pause", pause
                                                ]))

    def spawn_dns_command(self, args):
        # args format is domain=<domain>;resolvers=<resolvers>;record_types=<record_types>
        args = args.strip("'")
        args = args.strip('"')
        options = args.split(';')
        domain = ''
        resolvers = ''
        record_types = ''
        pause = '60'
        for option in options:
            key, value = option.split('=')
            if key == 'domain':
                domain = value
            elif key == 'resolvers':
                resolvers = value
            elif key == 'record_types':
                record_types = value
            elif key == 'pause':
                pause = value
        # Run the dns script
        self.processes.append(subprocess.Popen([self.python_exe, self.dns_script, 
                                                "--domain", domain, "--resolvers", resolvers, "--record_types", record_types,
                                                "--slack_webhook_url", self.args.slack_webhook_url,
                                                "--pause", pause
                                                ]))

    def serve_forever(self):
        if self.args.whois:
            for args in self.args.whois:
                self.spawn_whois_command(args)
                time.sleep(0.2)
        if self.args.dns:
            for args in self.args.dns:
                self.spawn_dns_command(args)
                time.sleep(0.2)
        for process in self.processes:
            process.wait()

if __name__ == '__main__':
    Runner().serve_forever()

