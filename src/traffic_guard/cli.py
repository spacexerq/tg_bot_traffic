from __future__ import annotations

import argparse
from pathlib import Path

from traffic_guard.config import load_settings
from traffic_guard.service import format_bytes_as_gb, run_check, run_daemon
from traffic_guard.telegram_client import send_message
from traffic_guard.traffic import current_period_utc, read_all_interface_stats, read_traffic_snapshot


def format_bytes(value: int) -> str:
    return f"{format_bytes_as_gb(value):.2f} GB"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Traffic Guard")
    parser.add_argument("--env-file", type=Path, help="Load variables from an env file before running")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check-once", help="Read counters, update state and send alerts if needed")
    subparsers.add_parser("daemon", help="Run periodic checks forever")
    subparsers.add_parser("test-message", help="Send a Telegram test message")
    subparsers.add_parser("show-interfaces", help="Print all detected Linux interfaces and counters")
    doctor_parser = subparsers.add_parser("doctor", help="Run a first-launch smoke check")
    doctor_parser.add_argument("--send-test-message", action="store_true", help="Also send a Telegram test message")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = load_settings(args.env_file)

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

    if args.command == "show-interfaces":
        for interface in read_all_interface_stats():
            print(
                f"{interface.name}: rx={format_bytes(interface.rx_bytes)}, "
                f"tx={format_bytes(interface.tx_bytes)}, total={format_bytes(interface.total_bytes)}"
            )
        return

    if args.command == "doctor":
        snapshot = read_traffic_snapshot(settings.interface_include, settings.interface_exclude)
        print(f"Server name: {settings.server_name}")
        print(f"Period (UTC): {current_period_utc()}")
        print(f"Monthly limit: {settings.monthly_limit_gb:.2f} GB")
        print(f"State file: {settings.state_file}")
        print(f"Polling interval: {settings.check_interval_seconds} seconds")
        print(f"Alert thresholds: {', '.join(str(value) for value in settings.alert_thresholds)}")
        print(f"Selected interfaces: {', '.join(snapshot.interfaces)}")
        print(f"Current selected total counters: {format_bytes(snapshot.total_bytes)}")
        print("")
        print("Smoke-check result: local traffic counters are readable.")
        print("Note: first tracked usage starts from the first saved baseline, not from server boot time.")

        if args.send_test_message:
            send_message(
                settings.bot_token,
                settings.chat_id,
                (
                    f"[{settings.server_name}] Traffic Guard smoke-check passed.\n"
                    f"Selected interfaces: {', '.join(snapshot.interfaces)}\n"
                    f"Monthly limit: {settings.monthly_limit_gb:.2f} GB"
                ),
            )
            print("Telegram smoke-check message sent")
        return

    parser.error("Unknown command")
