"""Local static server for the built app (out/) under the GitHub Pages prefix
/arcana-paddhati — like the live site, but on 127.0.0.1 and a free port
(never 8899, the owner's staging port).

In-process use:   srv = Server(); srv.start(); srv.base -> http://127.0.0.1:PORT/arcana-paddhati
                  srv.stop()
Switch mode (offline deploy test): srv.version_suffix = "b" makes sw.js and
precache-manifest.json look like a new deploy; srv.delay slows every request.
CLI:              python qa/lib/server.py [PORT]   (serves until killed)
"""
import functools
import http.server
import os
import socket
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa  # noqa: E402

FORBIDDEN_PORTS = {8899}


def free_port():
    while True:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        if port not in FORBIDDEN_PORTS:
            return port


class _Handler(http.server.SimpleHTTPRequestHandler):
    server_ref = None  # set per server class

    def translate_path(self, path):
        p = path.split("?", 1)[0].split("#", 1)[0]
        if p.startswith(qa.PREFIX):
            p = p[len(qa.PREFIX):] or "/"
        return super().translate_path(p)

    def end_headers(self):
        if self.path.split("?")[0].endswith(("sw.js", "precache-manifest.json")):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        srv = self.server_ref
        if srv.delay and "/sw.js" not in self.path:
            time.sleep(srv.delay)
        name = self.path.split("?", 1)[0]
        if srv.version_suffix and name.endswith(("/sw.js", "/precache-manifest.json")):
            return self._patched(name)
        return super().do_GET()

    def _patched(self, name):
        """A 'new deploy': the build version gets a suffix in sw.js and the manifest."""
        srv = self.server_ref
        fn = self.translate_path(name)
        try:
            body = open(fn, "rb").read().decode("utf-8")
        except OSError:
            self.send_error(404)
            return
        v = srv.base_version()
        body = body.replace(v, v + srv.version_suffix).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript" if name.endswith(".js") else "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class _HTTPServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        # a browser that navigates away aborts its pending requests — not an error
        if isinstance(sys.exc_info()[1], (ConnectionError, BrokenPipeError, TimeoutError)):
            return
        super().handle_error(request, client_address)


class Server:
    def __init__(self, root=None, port=None):
        self.root = root or qa.OUT
        self.port = port or free_port()
        self.delay = 0.0
        self.version_suffix = ""
        self._httpd = None
        self._thread = None
        self._version = None

    def base_version(self):
        if self._version is None:
            import json
            self._version = json.load(open(os.path.join(self.root, "precache-manifest.json"), encoding="utf-8"))["version"]
        return self._version

    @property
    def origin(self):
        return f"http://127.0.0.1:{self.port}"

    @property
    def base(self):
        return self.origin + qa.PREFIX

    def start(self):
        handler = type("H", (_Handler,), {"server_ref": self})
        self._httpd = _HTTPServer(("127.0.0.1", self.port), functools.partial(handler, directory=self.root))
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else free_port()
    s = Server(port=port).start()
    print(s.base, flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        s.stop()
