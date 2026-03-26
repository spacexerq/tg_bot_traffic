from __future__ import annotations

import time

from traffic_guard.agent_client import AgentClientError, fetch_server_status, reset_server_counter
from traffic_guard.config import ControlServer, ControlSettings
from traffic_guard.control_storage import ControlState, load_control_state, save_control_state
from traffic_guard.telegram_client import TelegramError, answer_callback_query, get_updates, send_message


def run_control_bot(settings: ControlSettings) -> None:
    while True:
        process_control_bot_once(settings)
        time.sleep(settings.poll_interval_seconds)


def process_control_bot_once(settings: ControlSettings) -> int:
    state = load_control_state(settings.state_file)
    updates = get_updates(settings.bot_token, state.telegram_update_offset)
    handled = 0
    next_offset = state.telegram_update_offset

    try:
        for update in updates:
            next_offset = max(next_offset, update.update_id + 1)
            if update.chat_id != settings.command_chat_id:
                continue

            try:
                if update.callback_data:
                    handled += _handle_callback(settings, update.chat_id, update.callback_data, update.callback_query_id)
                    continue

                if not update.text:
                    continue

                command = update.text.strip().split()[0].lower()
                if command.startswith("/start") or command.startswith("/help") or command.startswith("/servers"):
                    _send_server_menu(settings, update.chat_id)
                    handled += 1
                    continue

                if command.startswith("/status"):
                    send_message(settings.bot_token, update.chat_id, _build_all_servers_status(settings), inline_keyboard=_server_menu_keyboard(settings))
                    handled += 1
                    continue
            except TelegramError:
                continue
            except AgentClientError as exc:
                send_message(settings.bot_token, update.chat_id, f"Control bot error: {exc}")
                handled += 1
    finally:
        save_control_state(settings.state_file, ControlState(telegram_update_offset=next_offset))

    return handled


def _handle_callback(settings: ControlSettings, chat_id: str, callback_data: str, callback_query_id: str | None) -> int:
    if callback_query_id is not None:
        try:
            answer_callback_query(settings.bot_token, callback_query_id, "OK")
        except TelegramError:
            pass

    if callback_data == "menu":
        _send_server_menu(settings, chat_id)
        return 1

    if callback_data == "status_all":
        send_message(settings.bot_token, chat_id, _build_all_servers_status(settings), inline_keyboard=_server_menu_keyboard(settings))
        return 1

    if callback_data.startswith("server:"):
        server = _server_by_index(settings, callback_data.split(":", maxsplit=1)[1])
        send_message(
            settings.bot_token,
            chat_id,
            _build_server_status_message(server, fetch_server_status(server)),
            inline_keyboard=_server_action_keyboard(settings, server),
        )
        return 1

    if callback_data.startswith("refresh:"):
        server = _server_by_index(settings, callback_data.split(":", maxsplit=1)[1])
        send_message(
            settings.bot_token,
            chat_id,
            _build_server_status_message(server, fetch_server_status(server)),
            inline_keyboard=_server_action_keyboard(settings, server),
        )
        return 1

    if callback_data.startswith("reset_prompt:"):
        server = _server_by_index(settings, callback_data.split(":", maxsplit=1)[1])
        send_message(
            settings.bot_token,
            chat_id,
            f"[{server.name}] confirm counter reset",
            inline_keyboard=[
                [{"text": "Confirm reset", "callback_data": f"reset_exec:{_server_index(settings, server)}"}],
                [{"text": "Back", "callback_data": f"server:{_server_index(settings, server)}"}],
            ],
        )
        return 1

    if callback_data.startswith("reset_exec:"):
        server = _server_by_index(settings, callback_data.split(":", maxsplit=1)[1])
        send_message(
            settings.bot_token,
            chat_id,
            _build_server_status_message(server, reset_server_counter(server), prefix="counter reset"),
            inline_keyboard=_server_action_keyboard(settings, server),
        )
        return 1

    return 0


def _send_server_menu(settings: ControlSettings, chat_id: str) -> None:
    send_message(
        settings.bot_token,
        chat_id,
        "Select a server:",
        inline_keyboard=_server_menu_keyboard(settings),
    )


def _server_menu_keyboard(settings: ControlSettings) -> list[list[dict[str, str]]]:
    keyboard: list[list[dict[str, str]]] = [[{"text": "Status all", "callback_data": "status_all"}]]
    for index, server in enumerate(settings.servers):
        keyboard.append([{"text": server.name, "callback_data": f"server:{index}"}])
    return keyboard


def _server_action_keyboard(settings: ControlSettings, server: ControlServer) -> list[list[dict[str, str]]]:
    index = _server_index(settings, server)
    return [
        [{"text": "Refresh", "callback_data": f"refresh:{index}"}],
        [{"text": "Reset counter", "callback_data": f"reset_prompt:{index}"}],
        [{"text": "Back to servers", "callback_data": "menu"}],
    ]


def _build_all_servers_status(settings: ControlSettings) -> str:
    lines = ["Available server statuses:"]
    for server in settings.servers:
        try:
            payload = fetch_server_status(server)
            lines.append(_one_line_status(payload))
        except AgentClientError as exc:
            lines.append(f"- {server.name}: unavailable ({exc})")
    return "\n".join(lines)


def _build_server_status_message(server: ControlServer, payload: dict[str, object], prefix: str | None = None) -> str:
    header = f"[{server.name}]"
    if prefix:
        header = f"{header} {prefix}"
    interfaces = ", ".join(str(item) for item in payload.get("interfaces", []))
    used_gb = float(payload.get("used_gb", 0.0))
    limit_gb = float(payload.get("limit_gb", 0.0))
    usage_percent = float(payload.get("usage_percent", 0.0))
    remaining_gb = float(payload.get("remaining_gb", 0.0))
    return (
        f"{header}\n"
        f"Used this month: {used_gb:.2f} GB / {limit_gb:.2f} GB ({usage_percent:.2f}%)\n"
        f"Remaining to limit: {remaining_gb:.2f} GB\n"
        f"Period: {payload.get('period')}\n"
        f"Interfaces: {interfaces}"
    )


def _one_line_status(payload: dict[str, object]) -> str:
    used_gb = float(payload.get("used_gb", 0.0))
    limit_gb = float(payload.get("limit_gb", 0.0))
    usage_percent = float(payload.get("usage_percent", 0.0))
    return (
        f"- {payload.get('server_name')}: "
        f"{used_gb:.2f} / {limit_gb:.2f} GB "
        f"({usage_percent:.2f}%)"
    )


def _server_by_index(settings: ControlSettings, raw_index: str) -> ControlServer:
    return settings.servers[int(raw_index)]


def _server_index(settings: ControlSettings, server: ControlServer) -> int:
    return settings.servers.index(server)
