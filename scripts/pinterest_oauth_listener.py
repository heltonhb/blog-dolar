#!/usr/bin/env python3
"""Escuta o redirect do Pinterest OAuth e grava o `code` em arquivo."""

import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

OUT = Path(os.environ.get("PINTEREST_CODE_FILE", "/tmp/pinterest_code.json"))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        code = (q.get("code") or [None])[0]
        state = (q.get("state") or [None])[0]
        err = (q.get("error") or [None])[0]
        if code:
            OUT.write_text(json.dumps({"code": code, "state": state}))
            body = b"<h1>Code recebido!</h1><p>Pode fechar esta aba e voltar ao terminal.</p>"
            self.send_response(200)
        elif err:
            OUT.write_text(
                json.dumps({"error": err, "error_description": (q.get("error_description") or [""])[0]})
            )
            body = f"<h1>Erro: {err}</h1><p>Voltar ao terminal.</p>".encode()
            self.send_response(400)
        else:
            body = b"<h1>Esperando autorizacao do Pinterest...</h1>"
            self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    OUT.unlink(missing_ok=True)
    print(f"listening on http://localhost:{PORT}/ -> {OUT}", flush=True)
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
