from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest

from quanx_rules.upstream import download_snapshot, resolve_snapshot
from tests.helpers import SHA


class UpstreamTests(unittest.TestCase):
    def server(self, handler):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def cleanup():
            server.shutdown()
            server.server_close()
            thread.join()
        self.addCleanup(cleanup)
        return f"http://127.0.0.1:{server.server_port}"

    def test_commit_lookup_retries_and_returns_a_pinned_sha(self):
        class Handler(BaseHTTPRequestHandler):
            attempts = 0
            def do_GET(self):
                Handler.attempts += 1
                if Handler.attempts == 1:
                    self.send_response(503)
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(('{"sha":"' + SHA + '"}').encode())
            def log_message(self, *args):
                pass
        self.assertEqual(resolve_snapshot(api_url=self.server(Handler), retry_delay=0), SHA)

    def test_truncated_http_download_never_replaces_good_cache(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Length", "100")
                self.end_headers()
                self.wfile.write(b"incomplete")
            def log_message(self, *args):
                pass
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "src.tgz"
            dest.write_bytes(b"previous")
            with self.assertRaises(Exception):
                download_snapshot(SHA, dest, archive_url=self.server(Handler), retry_delay=0)
            self.assertEqual(dest.read_bytes(), b"previous")
