from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime

from traffic_guard.config import Settings
from traffic_guard.storage import State, load_state, save_state
from traffic_guard.telegram_client import send_message
from traffic_guard.traffic import current_period_utc, read_traffic_snapshot


@dataclass(slots=True)
class CheckResult:
    period: str
    accumulated_bytes: int
    usage_percent: float
    triggered_thresholds: list[int]
    interfaces: list[str]


def format_bytes_as_gb(value: int) -> float:
    return value / (1024 * 1024 * 1024)


def format_alert(settings: Settings, result: CheckResult, threshold: int) -> str:
    used_gb = format_bytes_as_gb(result.accumulated_bytes)
    limit_gb = settings.monthly_limit_gb
    interfaces = ", ".join(result.interfaces)
    return (
        f"[{settings.server_name}] traffic alert\n"
        f"Threshold: {threshold}%\n"
        f"Used: {used_gb:.2f} GB / {limit_gb:.2f} GB ({result.usage_percent:.2f}%)\n"
        f"Period: {result.period}\n"
        f"Interfaces: {interfaces}"
    )


def format_daily_report(settings: Settings, result: CheckResult, report_date: str) -> str:
    used_gb = format_bytes_as_gb(result.accumulated_bytes)
    remaining_gb = max(settings.monthly_limit_gb - used_gb, 0)
    interfaces = ", ".join(result.interfaces)
    return (
        f"[{settings.server_name}] daily traffic report\n"
        f"Date: {report_date} ({settings.daily_report_timezone})\n"
        f"Used this month: {used_gb:.2f} GB / {settings.monthly_limit_gb:.2f} GB ({result.usage_percent:.2f}%)\n"
        f"Remaining to limit: {remaining_gb:.2f} GB\n"
        f"Period: {result.period}\n"
        f"Interfaces: {interfaces}"
    )


def run_check(settings: Settings, send_notifications: bool = True, force_daily_report: bool = False) -> CheckResult:
    period = current_period_utc()
    state = load_state(settings.state_file, period)
    snapshot = read_traffic_snapshot(settings.interface_include, settings.interface_exclude)

    accumulated_bytes = _calculate_accumulated_bytes(state, snapshot.total_bytes)
    usage_percent = (accumulated_bytes / settings.monthly_limit_bytes) * 100
    triggered_thresholds = [
        threshold
        for threshold in settings.alert_thresholds
        if usage_percent >= threshold and threshold not in state.notified_thresholds
    ]

    state.accumulated_bytes = accumulated_bytes
    state.last_total_bytes = snapshot.total_bytes
    state.notified_thresholds.extend(triggered_thresholds)
    state.notified_thresholds = sorted(set(state.notified_thresholds))
    save_state(settings.state_file, state)

    result = CheckResult(
        period=period,
        accumulated_bytes=accumulated_bytes,
        usage_percent=usage_percent,
        triggered_thresholds=triggered_thresholds,
        interfaces=snapshot.interfaces,
    )

    if send_notifications:
        for threshold in triggered_thresholds:
            send_message(settings.bot_token, settings.chat_id, format_alert(settings, result, threshold))
        if _should_send_daily_report(settings, state) or force_daily_report:
            report_date = _current_report_date(settings)
            send_message(settings.bot_token, settings.chat_id, format_daily_report(settings, result, report_date))
            state.last_daily_report_date = report_date
            save_state(settings.state_file, state)

    return result


def run_daemon(settings: Settings) -> None:
    while True:
        run_check(settings, send_notifications=True)
        time.sleep(settings.check_interval_seconds)


def _calculate_accumulated_bytes(state: State, current_total_bytes: int) -> int:
    if state.last_total_bytes is None:
        return state.accumulated_bytes

    if current_total_bytes >= state.last_total_bytes:
        delta = current_total_bytes - state.last_total_bytes
    else:
        # Interface counters likely reset after reboot, so we start a new baseline.
        delta = current_total_bytes

    return state.accumulated_bytes + delta


def _current_report_date(settings: Settings) -> str:
    return datetime.now(settings.daily_report_zoneinfo).date().isoformat()


def _should_send_daily_report(settings: Settings, state: State) -> bool:
    if not settings.daily_report_enabled:
        return False

    now = datetime.now(settings.daily_report_zoneinfo)
    report_date = now.date().isoformat()
    if state.last_daily_report_date == report_date:
        return False

    scheduled_minutes = settings.daily_report_hour * 60 + settings.daily_report_minute
    now_minutes = now.hour * 60 + now.minute
    return now_minutes >= scheduled_minutes
