from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from traffic_guard.config import Settings
from traffic_guard.service import reset_counter, run_check, status_payload


def run_agent_api(settings: Settings) -> None:
    host = os.environ.get("TG_AGENT_BIND", "0.0.0.0")
    port = int(os.environ.get("TG_AGENT_PORT", "8787"))
    api_token = os.environ["TG_AGENT_TOKEN"]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/status":
                if not _is_authorized(self.headers.get("X-Traffic-Guard-Token"), api_token):
                    self._write_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                    return
                result = run_check(settings, send_notifications=False)
                self._write_json(HTTPStatus.OK, status_payload(settings, result))
                return

            if self.path == "/health":
                self._write_json(HTTPStatus.OK, {"ok": True, "server_name": settings.server_name})
                return

            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path == "/reset":
                if not _is_authorized(self.headers.get("X-Traffic-Guard-Token"), api_token):
                    self._write_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                    return
                result = reset_counter(settings)
                self._write_json(HTTPStatus.OK, status_payload(settings, result))
                return

            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def _write_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer((host, port), Handler)
    server.serve_forever()


def _is_authorized(received_token: str | None, expected_token: str) -> bool:
    return received_token == expected_token
