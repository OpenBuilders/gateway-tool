import logging
import socketserver
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler


logger = logging.getLogger(__name__)


def start_health_check_server(is_healthy_callback: Callable[[], bool]):
    class HealthCheckHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                # Pass the service as an argument
                if is_healthy_callback():
                    self.send_response(200, "OK")
                    self.end_headers()
                    self.wfile.write(b"OK")
                else:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(b"Not Connected")
            else:
                self.send_response(404)
                self.end_headers()

    with socketserver.TCPServer(("", 8080), HealthCheckHandler) as httpd:
        logger.info("Health check server running on port 8080")
        httpd.serve_forever()
