from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import error, parse, request


class TelegramError(RuntimeError):
    pass


@dataclass(slots=True)
class TelegramUpdate:
    update_id: int
    chat_id: str
    text: str


def _read_json_response(req: request.Request) -> dict:
    try:
        with request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
    except error.URLError as exc:
        raise TelegramError(f"Telegram request failed: {exc}") from exc

    parsed = json.loads(body)
    if not parsed.get("ok"):
        raise TelegramError(f"Telegram API error: {parsed}")
    return parsed


def send_message(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
        }
    ).encode("utf-8")
    req = request.Request(url, data=payload, method="POST")
    _read_json_response(req)


def get_updates(bot_token: str, offset: int) -> list[TelegramUpdate]:
    query = parse.urlencode(
        {
            "offset": offset,
            "timeout": 0,
            "allowed_updates": json.dumps(["message"]),
        }
    )
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates?{query}"
    req = request.Request(url, method="GET")
    parsed = _read_json_response(req)

    updates: list[TelegramUpdate] = []
    for item in parsed.get("result", []):
        message = item.get("message") or {}
        chat = message.get("chat") or {}
        text = message.get("text")
        chat_id = chat.get("id")
        update_id = item.get("update_id")
        if text is None or chat_id is None or update_id is None:
            continue
        updates.append(TelegramUpdate(update_id=int(update_id), chat_id=str(chat_id), text=str(text)))

    return updates
