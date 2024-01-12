import sys
import socket
import random
import string
import logging

RESPONSE_SAMPLE = {
                "Domain Name": "DUMMY.NET",
                "Registry Domain ID": "1234567890_DOMAIN_NET",
                "Registrar WHOIS Server": "whois.dummy",
                "Registrar URL": "https://dummy",
                "Updated Date": "2024-01-05T19:20:52Z",
                "Creation Date": "2011-04-17T05:37:16Z",
                "Registry Expiry Date": "2080-04-17T05:37:16Z",
                "Registrar": "DUMMY",
                "Registrar IANA ID": "2",
                "Registrar Abuse Contact Email": "domain.operations@dummy",
                "Registrar Abuse Contact Phone": "+1.5556667777",
                "Domain Status": "clientTransferProhibited https://icann.org/epp#clientTransferProhibited",
                "DNSSEC": "unsigned"
}

def run_server(host='127.0.0.1', port=43):
    # Create a TCP/IP socket
    logger = logging.getLogger("WHOISTestServer")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    fh = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(fh)
    logger.addHandler(ch)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Bind the socket to the address and port
    server_address = (host, port)
    logger.info(f"Starting up WHOIS server on {host} port {port}")
    sock.bind(server_address)
    
    # Listen for incoming connections
    sock.listen(1)
    
    while True:
        # Wait for a connection
        connection, client_address = sock.accept()
        try:
            logger.info(f"Connection from {client_address}")

            # Receive the data in small chunks
            data = connection.recv(1024)
            logger.info(f"Received: {data.decode()}")

            # Prepare and send a response
            random_keys = random.sample(list(RESPONSE_SAMPLE.keys()), random.randint(1, 3))
            response = ""
            for key, value in RESPONSE_SAMPLE.items():
                if key in random_keys:
                    new_value = "".join(random.sample(string.ascii_letters, random.randint(1, 20)))
                else:
                    new_value = value
                response += f"{key}: {new_value}\n"
            for x in range(random.randint(1, 4)):
                name_server = "".join(random.sample(string.ascii_letters, random.randint(1, 20)))
                response += f"Name Server: {name_server}\n"
            logger.info(f"Sending response")
            connection.sendall(response.encode())

        finally:
            # Clean up the connection
            connection.close()

if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("Shutting down WHOIS server")
    sys.exit(0)

