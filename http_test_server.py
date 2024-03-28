import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl
import random
import sys

logger = logging.getLogger("HTTPTestServer")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
fh = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(fh)
logger.addHandler(ch)

class HelloWorldHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        logger.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        # Send response status code
        code = random.choice([200, 201, 202, 401, 404, 500, 503])
        self.send_response(code)

        # Send headers
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

        # Send the html message
        self.wfile.write(b"Hello, World!")
        logger.info("Response sent.")

def run_server(host='localhost', port=7777):
    # Server settings
    logger.info(f"Starting up HTTP server on {host} port {port}")
    httpd = HTTPServer((host, port), HelloWorldHandler)
    httpd.socket = ssl.wrap_socket(httpd.socket, keyfile="/app/key.pem", certfile="/app/certificate.pem", server_side=True)
    httpd.serve_forever()
    logger.info("Stopping HTTP server")

if __name__ == '__main__':
    try:
        run_server()
    except KeyboardInterrupt:
        print("Shutting down HTTP server")
    sys.exit(0)
