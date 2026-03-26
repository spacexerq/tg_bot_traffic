from __future__ import annotations

import json
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
    command_chat_id: str
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
    monthly_reset_hour: int
    monthly_reset_minute: int
    monthly_reset_timezone: str
    control_bot_token: str | None
    control_notify_chat_id: str | None

    @property
    def monthly_limit_bytes(self) -> int:
        return int(self.monthly_limit_gb * 1024 * 1024 * 1024)

    @property
    def daily_report_zoneinfo(self) -> ZoneInfo:
        return ZoneInfo(self.daily_report_timezone)

    @property
    def monthly_reset_zoneinfo(self) -> ZoneInfo:
        return ZoneInfo(self.monthly_reset_timezone)


@dataclass(slots=True)
class ControlServer:
    name: str
    base_url: str
    api_token: str


@dataclass(slots=True)
class ControlSettings:
    bot_token: str
    command_chat_id: str
    servers_file: Path
    state_file: Path
    poll_interval_seconds: int
    servers: list[ControlServer]


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
    command_chat_id = os.environ.get("TG_COMMAND_CHAT_ID", chat_id)
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
    monthly_reset_hour = int(os.environ.get("TG_MONTHLY_RESET_HOUR", "0"))
    monthly_reset_minute = int(os.environ.get("TG_MONTHLY_RESET_MINUTE", "1"))
    monthly_reset_timezone = os.environ.get("TG_MONTHLY_RESET_TIMEZONE", daily_report_timezone)
    control_bot_token = os.environ.get("TG_CONTROL_BOT_TOKEN")
    control_notify_chat_id = os.environ.get("TG_CONTROL_NOTIFY_CHAT_ID", command_chat_id)

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
    if not 0 <= monthly_reset_hour <= 23:
        raise ValueError("TG_MONTHLY_RESET_HOUR must be between 0 and 23")
    if not 0 <= monthly_reset_minute <= 59:
        raise ValueError("TG_MONTHLY_RESET_MINUTE must be between 0 and 59")
    ZoneInfo(daily_report_timezone)
    ZoneInfo(monthly_reset_timezone)

    return Settings(
        bot_token=bot_token,
        chat_id=chat_id,
        command_chat_id=command_chat_id,
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
        monthly_reset_hour=monthly_reset_hour,
        monthly_reset_minute=monthly_reset_minute,
        monthly_reset_timezone=monthly_reset_timezone,
        control_bot_token=control_bot_token,
        control_notify_chat_id=control_notify_chat_id,
    )


def load_control_settings(env_file: Path | None = None) -> ControlSettings:
    if env_file is not None:
        load_env_file(env_file)

    bot_token = os.environ["TG_BOT_TOKEN"]
    command_chat_id = os.environ["TG_COMMAND_CHAT_ID"]
    servers_file = Path(os.environ.get("TG_CONTROL_SERVERS_FILE", "/etc/traffic-guard/control-servers.json"))
    state_file = Path(os.environ.get("TG_CONTROL_STATE_FILE", "/var/lib/traffic-guard/control-bot-state.json"))
    poll_interval_seconds = int(os.environ.get("TG_CONTROL_POLL_INTERVAL_SECONDS", "5"))

    if poll_interval_seconds <= 0:
        raise ValueError("TG_CONTROL_POLL_INTERVAL_SECONDS must be greater than zero")

    servers = _load_control_servers(servers_file)
    if not servers:
        raise ValueError(f"No control servers configured in {servers_file}")

    return ControlSettings(
        bot_token=bot_token,
        command_chat_id=command_chat_id,
        servers_file=servers_file,
        state_file=state_file,
        poll_interval_seconds=poll_interval_seconds,
        servers=servers,
    )


def _load_control_servers(path: Path) -> list[ControlServer]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_servers = data.get("servers", data) if isinstance(data, dict) else data

    servers: list[ControlServer] = []
    for item in raw_servers:
        servers.append(
            ControlServer(
                name=str(item["name"]),
                base_url=str(item["base_url"]).rstrip("/"),
                api_token=str(item["api_token"]),
            )
        )
    return servers
