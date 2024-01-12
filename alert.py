import os
from utils import slack, get_region, get_sensor_id
import argparse

if __name__ == '__main__':
    region = get_region()
    domain = os.getenv('DOMAIN', None)
    whois_domain = os.getenv('WHOIS_DOMAIN', None)
    if not whois_domain:
        whois_domain = domain
    dns_domains = os.getenv('DNS_DOMAINS', None)
    if not dns_domains:
        dns_domains = [domain]
    else:
        dns_domains = dns_domains.split(',')
    test_mode = os.getenv('TEST_MODE', None)
    if test_mode == "1":
        domain = 'dummy.net'
        whois_domain = domain
        dns_domains = [domain]
    parser = argparse.ArgumentParser()
    parser.add_argument('--message', type=str, default='Hello World!')
    parser.add_argument('--slack_webhook_url', type=str, default=None)
    args = parser.parse_args()
    if args.slack_webhook_url:
        prefix = f'[id={get_sensor_id()}][geo={get_region()}][domain={whois_domain}]'
        msg = f':alert: *[WHOISMonitor]{prefix}*\n{args.message}'
        slack(msg, args.slack_webhook_url)
        for dns_domain in dns_domains:
            msg = f':alert: *[DNSRecordMonitor]{prefix}*\n{args.message}'
            slack(msg, args.slack_webhook_url)
