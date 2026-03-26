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
    text: str | None = None
    callback_data: str | None = None
    callback_query_id: str | None = None


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


def send_message(
    bot_token: str,
    chat_id: str,
    text: str,
    inline_keyboard: list[list[dict[str, str]]] | None = None,
) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload_data: dict[str, str] = {
        "chat_id": chat_id,
        "text": text,
    }
    if inline_keyboard is not None:
        payload_data["reply_markup"] = json.dumps({"inline_keyboard": inline_keyboard})
    payload = parse.urlencode(payload_data).encode("utf-8")
    req = request.Request(url, data=payload, method="POST")
    _read_json_response(req)


def answer_callback_query(bot_token: str, callback_query_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
    payload = parse.urlencode(
        {
            "callback_query_id": callback_query_id,
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
            "allowed_updates": json.dumps(["message", "callback_query"]),
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
        if text is not None and chat_id is not None and update_id is not None:
            updates.append(TelegramUpdate(update_id=int(update_id), chat_id=str(chat_id), text=str(text)))
            continue

        callback_query = item.get("callback_query") or {}
        callback_id = callback_query.get("id")
        callback_data = callback_query.get("data")
        callback_message = callback_query.get("message") or {}
        callback_chat = callback_message.get("chat") or {}
        callback_chat_id = callback_chat.get("id")
        if callback_id is None or callback_data is None or callback_chat_id is None or update_id is None:
            continue
        updates.append(
            TelegramUpdate(
                update_id=int(update_id),
                chat_id=str(callback_chat_id),
                callback_data=str(callback_data),
                callback_query_id=str(callback_id),
            )
        )

    return updates
