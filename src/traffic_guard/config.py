from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(slots=True)
class Settings:
    bot_token: str
    chat_id: str
    server_name: str
    monthly_limit_gb: float
    alert_thresholds: list[int]
    interface_include: list[str]
    interface_exclude: list[str]
    state_file: Path
    check_interval_seconds: int
    daily_report_enabled: bool
    daily_report_hour: int
    daily_report_minute: int
    daily_report_timezone: str

    @property
    def monthly_limit_bytes(self) -> int:
        return int(self.monthly_limit_gb * 1024 * 1024 * 1024)

    @property
    def daily_report_zoneinfo(self) -> ZoneInfo:
        return ZoneInfo(self.daily_report_timezone)


def load_env_file(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def load_settings(env_file: Path | None = None) -> Settings:
    if env_file is not None:
        load_env_file(env_file)

    bot_token = os.environ["TG_BOT_TOKEN"]
    chat_id = os.environ["TG_CHAT_ID"]
    server_name = os.environ.get("TG_SERVER_NAME", "unknown-server")
    monthly_limit_gb = float(os.environ["TG_MONTHLY_LIMIT_GB"])
    thresholds = sorted({int(item) for item in _split_csv(os.environ.get("TG_ALERT_THRESHOLDS", "80,90,100"))})
    include = _split_csv(os.environ.get("TG_INTERFACE_INCLUDE", ""))
    exclude = _split_csv(os.environ.get("TG_INTERFACE_EXCLUDE", "lo,docker0,veth"))
    state_file = Path(os.environ.get("TG_STATE_FILE", "/var/lib/traffic-guard/state.json"))
    interval = int(os.environ.get("TG_CHECK_INTERVAL_SECONDS", "300"))
    daily_report_enabled = os.environ.get("TG_DAILY_REPORT_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    daily_report_hour = int(os.environ.get("TG_DAILY_REPORT_HOUR", "9"))
    daily_report_minute = int(os.environ.get("TG_DAILY_REPORT_MINUTE", "0"))
    daily_report_timezone = os.environ.get("TG_DAILY_REPORT_TIMEZONE", "Europe/Moscow")

    if not thresholds:
        raise ValueError("TG_ALERT_THRESHOLDS must contain at least one value")
    if monthly_limit_gb <= 0:
        raise ValueError("TG_MONTHLY_LIMIT_GB must be greater than zero")
    if interval <= 0:
        raise ValueError("TG_CHECK_INTERVAL_SECONDS must be greater than zero")
    if not 0 <= daily_report_hour <= 23:
        raise ValueError("TG_DAILY_REPORT_HOUR must be between 0 and 23")
    if not 0 <= daily_report_minute <= 59:
        raise ValueError("TG_DAILY_REPORT_MINUTE must be between 0 and 59")
    ZoneInfo(daily_report_timezone)

    return Settings(
        bot_token=bot_token,
        chat_id=chat_id,
        server_name=server_name,
        monthly_limit_gb=monthly_limit_gb,
        alert_thresholds=thresholds,
        interface_include=include,
        interface_exclude=exclude,
        state_file=state_file,
        check_interval_seconds=interval,
        daily_report_enabled=daily_report_enabled,
        daily_report_hour=daily_report_hour,
        daily_report_minute=daily_report_minute,
        daily_report_timezone=daily_report_timezone,
    )
