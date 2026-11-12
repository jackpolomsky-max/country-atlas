"""Local server for the Country Atlas dashboard.

Run:   python3 server.py
Open:  http://localhost:8000

It serves country-dashboard.html and forwards data requests to the country
API with your key attached, because browsers block direct calls to it.
Keep this file next to country-dashboard.html.
"""
import glob
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))


def load_key():
    """Key comes from the RESTCOUNTRIES_KEY setting, or from api_key.txt next to this file (local use only)."""
    key = os.environ.get("RESTCOUNTRIES_KEY", "").strip()
    if not key:
        try:
            with open(os.path.join(HERE, "api_key.txt")) as f:
                key = f.read().strip()
        except OSError:
            pass
    return key


API_KEY = load_key()
PORT = int(os.environ.get("PORT", "8000"))
# Hosts set PORT; listen on all interfaces there, and only on this computer when run locally.
HOST = "0.0.0.0" if "PORT" in os.environ else "127.0.0.1"


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, ctype="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _forward(self, url, headers=None):
        req = urllib.request.Request(url, headers=dict(headers or {}, **{"User-Agent": "country-atlas/1.0", "Accept": "application/json"}))
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                self._send(r.status, r.read())
        except urllib.error.HTTPError as e:
            self._send(e.code, e.read() or json.dumps({"error": str(e)}).encode())
        except Exception as e:  # network or DNS failure
            self._send(502, json.dumps({"error": str(e)}).encode())

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            pages = glob.glob(os.path.join(HERE, "country-dashboard*.html"))
            if not pages:
                msg = ("No country-dashboard*.html file found in:\n%s\n"
                       "Put the dashboard page in the same folder as server.py, then reload." % HERE)
                return self._send(404, msg.encode(), "text/plain; charset=utf-8")
            newest = max(pages, key=os.path.getmtime)
            with open(newest, "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if path == "/api/v5":
            q = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
            url = "https://api.restcountries.com/countries/v5?q=" + urllib.parse.quote(q)
            return self._forward(url, {"Authorization": "Bearer " + API_KEY})
        if path.startswith("/api/v3/alpha/"):
            code = urllib.parse.quote(path.rsplit("/", 1)[1])
            return self._forward("https://restcountries.com/v3.1/alpha/" + code)
        self._send(404, b'{"error":"not found"}')

    def log_message(self, fmt, *args):
        print(self.address_string(), fmt % args)


if __name__ == "__main__":
    if not API_KEY:
        print("WARNING: no API key found. Set RESTCOUNTRIES_KEY or create api_key.txt containing the key.")
    print("Country Atlas running on port %d  (Ctrl+C to stop)" % PORT)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
