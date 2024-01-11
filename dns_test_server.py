import random
import socket
import logging
from dnslib import DNSRecord, RR, QTYPE, A, AAAA, MX, NS, TXT, CNAME, SOA
from dnslib.server import DNSServer, BaseResolver, DNSLogger

logger = logging.getLogger("DNSTestServer")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
fh = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(fh)
logger.addHandler(ch)

l = logging.getLogger("[DNSHandler:RandomDNSResolver]")
l.setLevel(logging.ERROR)
l.addHandler(ch)


class RandomDNSResolver(BaseResolver):
    def __init__(self, ttl=60):
        self.ttl = ttl

    def resolve(self, request, handler):
        reply = request.reply()
        qname = request.q.qname
        qtype = QTYPE[request.q.qtype]

        if qtype == 'A':
            ip = socket.inet_ntoa(random.randint(0, 0xFFFFFFFF).to_bytes(4, 'big'))
            rr = RR(qname, QTYPE.A, rdata=A(ip), ttl=self.ttl)
            reply.add_answer(rr)
            logger.debug(f"Resolved {qname} {qtype} to {ip}")

        elif qtype == 'AAAA':
            ip = socket.inet_ntop(socket.AF_INET6, random.randint(0, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF).to_bytes(16, 'big'))
            rr = RR(qname, QTYPE.AAAA, rdata=AAAA(ip), ttl=self.ttl)
            reply.add_answer(rr)
            logger.debug(f"Resolved {qname} {qtype} to {ip}")

        elif qtype == 'MX':
            mailserver = f'mail{random.randint(1, 100)}.dummy.net'
            rr = RR(qname, QTYPE.MX, rdata=MX(mailserver), ttl=self.ttl)
            reply.add_answer(rr)
            logger.debug(f"Resolved {qname} {qtype} to {mailserver}")

        elif qtype == 'NS':
            nameserver = f'ns{random.randint(1, 100)}.dummy.net'
            rr = RR(qname, QTYPE.NS, rdata=NS(nameserver), ttl=self.ttl)
            reply.add_answer(rr)
            logger.debug(f"Resolved {qname} {qtype} to {nameserver}")

        elif qtype == 'TXT':
            txt_data = f'text{random.randint(1, 100)}'
            rr = RR(qname, QTYPE.TXT, rdata=TXT(txt_data), ttl=self.ttl)
            reply.add_answer(rr)
            logger.debug(f"Resolved {qname} {qtype} to {txt_data}")

        elif qtype == 'CNAME':
            cname = f'alias{random.randint(1, 100)}.dummy.net'
            rr = RR(qname, QTYPE.CNAME, rdata=CNAME(cname), ttl=self.ttl)
            reply.add_answer(rr)
            logger.debug(f"Resolved {qname} {qtype} to {cname}")

        elif qtype == 'SOA':
            mname = f'ns{random.randint(1, 100)}.dummy.net'
            rname = f'admin{random.randint(1, 100)}.dummy.net'
            rr = RR(qname, QTYPE.SOA, rdata=SOA(mname, rname), ttl=self.ttl)
            reply.add_answer(rr)
            logger.debug(f"Resolved {qname} {qtype} to {mname} {rname}")

        return reply

def run():
    resolver = RandomDNSResolver()
    logger.info("Starting DNS server")
    server = DNSServer(resolver, port=53, address="127.0.0.1", logger=DNSLogger(prefix=False,logf=lambda s:s))
    server.start()
    logger.info("Stopping DNS server")

if __name__ == '__main__':
    run()

