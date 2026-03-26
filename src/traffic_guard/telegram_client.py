from __future__ import annotations

import json
from urllib import error, parse, request


class TelegramError(RuntimeError):
    pass


def send_message(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
        }
    ).encode("utf-8")
    req = request.Request(url, data=payload, method="POST")

    try:
        with request.urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8")
    except error.URLError as exc:
        raise TelegramError(f"Telegram request failed: {exc}") from exc

    parsed = json.loads(body)
    if not parsed.get("ok"):
        raise TelegramError(f"Telegram API error: {parsed}")
