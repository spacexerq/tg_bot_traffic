from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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

    @property
    def monthly_limit_bytes(self) -> int:
        return int(self.monthly_limit_gb * 1024 * 1024 * 1024)


def load_settings() -> Settings:
    bot_token = os.environ["TG_BOT_TOKEN"]
    chat_id = os.environ["TG_CHAT_ID"]
    server_name = os.environ.get("TG_SERVER_NAME", "unknown-server")
    monthly_limit_gb = float(os.environ["TG_MONTHLY_LIMIT_GB"])
    thresholds = sorted({int(item) for item in _split_csv(os.environ.get("TG_ALERT_THRESHOLDS", "80,90,100"))})
    include = _split_csv(os.environ.get("TG_INTERFACE_INCLUDE", ""))
    exclude = _split_csv(os.environ.get("TG_INTERFACE_EXCLUDE", "lo,docker0,veth"))
    state_file = Path(os.environ.get("TG_STATE_FILE", "/var/lib/traffic-guard/state.json"))
    interval = int(os.environ.get("TG_CHECK_INTERVAL_SECONDS", "300"))

    if not thresholds:
        raise ValueError("TG_ALERT_THRESHOLDS must contain at least one value")
    if monthly_limit_gb <= 0:
        raise ValueError("TG_MONTHLY_LIMIT_GB must be greater than zero")
    if interval <= 0:
        raise ValueError("TG_CHECK_INTERVAL_SECONDS must be greater than zero")

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
    )
