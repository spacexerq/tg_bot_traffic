from __future__ import annotations

import argparse

from traffic_guard.config import load_settings
from traffic_guard.service import format_bytes_as_gb, run_check, run_daemon
from traffic_guard.telegram_client import send_message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Traffic Guard")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check-once", help="Read counters, update state and send alerts if needed")
    subparsers.add_parser("daemon", help="Run periodic checks forever")
    subparsers.add_parser("test-message", help="Send a Telegram test message")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = load_settings()

    if args.command == "check-once":
        result = run_check(settings, send_notifications=True)
        print(
            f"{settings.server_name}: {format_bytes_as_gb(result.accumulated_bytes):.2f} GB "
            f"used in {result.period} ({result.usage_percent:.2f}%)"
        )
        return

    if args.command == "daemon":
        run_daemon(settings)
        return

    if args.command == "test-message":
        send_message(settings.bot_token, settings.chat_id, f"[{settings.server_name}] Traffic Guard test message")
        print("Test message sent")
        return

    parser.error("Unknown command")
