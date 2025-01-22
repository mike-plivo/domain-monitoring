import sys
import subprocess
import time
import argparse


class Command(object):
    def __init__(self, python_exe, script, args):
        self.python_exe = python_exe
        self.script = script
        self.args = args
        self.process = None

    def __repr__(self):
        return "Command(python_exe=%s, script=%s, args=%s)" % (self.python_exe, self.script, self.args)

    def run(self):
        self.process = subprocess.Popen([self.python_exe, self.script] + self.args)

    def wait(self):
        return self.process.wait()


class Runner(object):
    WHOIS_SCRIPT = 'whois_monitor.py'
    DNS_SCRIPT = 'dns_monitor.py'
    HTTP_SCRIPT = 'http_monitor.py'

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
        # Adding the --http argument
        parser.add_argument('--http', action='append', 
                            help='Information for HTTP query. Can be specified multiple times. Format: --http=\'url=<URL>;method=<OPTIONAL>;timeout=<OPTIONAL>;connect_timeout=<OPTIONAL>;payload=<OPTIONAL>;headers=<OPTIONAL>;verify_ssl=<OPTIONAL>;>pause=<OPTIONAL>\'. Default method is GET. Default timeout is 15 seconds. Default connect_timeout is 5 seconds. Default payload is empty. Default headers are empty. Default verify_ssl is true. Default pause between each query is 60 seconds.')

        parser.add_argument("--slack_webhook_url", help="Slack webhook url (default disabled).", default='')
        parser.add_argument('--python_exe', help='Path to python executable', default='python3')
        parser.add_argument('--whois_script', help='Path to whois script', default=self.WHOIS_SCRIPT)
        parser.add_argument('--dns_script', help='Path to dns script', default=self.DNS_SCRIPT)
        parser.add_argument('--http_script', help='Path to http script', default=self.HTTP_SCRIPT)

        self.args = parser.parse_args()
        self.python_exe = self.args.python_exe or 'python3'
        self.whois_script = self.args.whois_script or self.WHOIS_SCRIPT
        self.dns_script = self.args.dns_script or self.DNS_SCRIPT
        self.http_script = self.args.http_script or self.HTTP_SCRIPT

    def _strip_and_split_args(self, args):
        return args.strip("'").strip('"').split(';')

    def spawn_whois_command(self, args):
        # args format is domain=<domain>;server=<optional>;timeout=30
        options = self._strip_and_split_args(args)
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
        p = Command(self.python_exe, self.whois_script, 
                          ["--domain", domain, "--whois_server", server, "--whois_timeout", timeout, 
                           "--slack_webhook_url", self.args.slack_webhook_url, "--pause", pause])
        p.run()
        self.processes.append(p)

    def spawn_dns_command(self, args):
        # args format is domain=<domain>;resolvers=<resolvers>;record_types=<record_types>
        options = self._strip_and_split_args(args)
        domain = ''
        resolvers = ''
        record_types = ''
        pause = '120'
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
        p = Command(self.python_exe, self.dns_script, 
                          ["--domain", domain, "--resolvers", resolvers, "--record_types", record_types,
                           "--slack_webhook_url", self.args.slack_webhook_url, "--pause", pause])
        p.run()
        self.processes.append(p)

    def spawn_http_command(self, args):
        # args format is url=<url>;method=<method>;timeout=<timeout>;connect_timeout=<connect_timeout>;payload=<payload>;headers=<headers>;verify_ssl=<verify_ssl>;pause=<pause>
        options = self._strip_and_split_args(args)
        url = ''
        method = 'GET'
        timeout = '15'
        connect_timeout = '5'
        payload = ''
        headers = ''
        verify_ssl = 'True'
        pause = '60'
        for option in options:
            key, value = option.split('=')
            if key == 'url':
                url = value
            elif key == 'method':
                method = value
            elif key == 'timeout':
                timeout = value
            elif key == 'connect_timeout':
                connect_timeout = value
            elif key == 'payload':
                payload = value
            elif key == 'headers':
                headers = value
            elif key == 'verify_ssl':
                verify_ssl = value
            elif key == 'pause':
                pause = value
        # Run the http script
        p = Command(self.python_exe, self.http_script, 
                          ["--url", url, "--method", method, "--timeout", timeout, "--connect_timeout", connect_timeout,
                           "--payload", payload, "--headers", headers, "--verify_ssl", verify_ssl,
                           "--slack_webhook_url", self.args.slack_webhook_url, "--pause", pause])
        p.run()
        self.processes.append(p)

    def start(self):
        if self.args.whois:
            for args in self.args.whois:
                self.spawn_whois_command(args)
                time.sleep(0.2)
        if self.args.dns:
            for args in self.args.dns:
                self.spawn_dns_command(args)
                time.sleep(0.2)
        if self.args.http:
            for args in self.args.http:
                self.spawn_http_command(args)
                time.sleep(0.2)
        if not self.processes:
            print("No process to start. Exiting.")
            return 1
        return 0

    def wait(self):
        errors = []
        for process in self.processes:
            rt = process.wait()
            if rt != 0:
                print(f"{process} failed with exit code: {rt}")
                errors.append(process)
        if errors:
            print(f"Errors occurred in the following processes: {errors}")
            return 1
        return 0

    def serve_forever(self):
        if self.start() != 0:
            sys.exit(1)
        if self.wait() != 0:
            sys.exit(1)


if __name__ == '__main__':
    Runner().serve_forever()

