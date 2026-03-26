from __future__ import annotations

import json
from urllib import error, request

from traffic_guard.config import ControlServer


class AgentClientError(RuntimeError):
    pass


def fetch_server_status(server: ControlServer) -> dict[str, object]:
    return _request_json(server, "/status", method="GET")


def reset_server_counter(server: ControlServer) -> dict[str, object]:
    return _request_json(server, "/reset", method="POST")


def _request_json(server: ControlServer, path: str, method: str) -> dict[str, object]:
    req = request.Request(f"{server.base_url}{path}", method=method)
    req.add_header("X-Traffic-Guard-Token", server.api_token)
    req.add_header("Accept", "application/json")

    try:
        with request.urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8")
    except error.URLError as exc:
        raise AgentClientError(f"{server.name}: {exc}") from exc

    return json.loads(body)
