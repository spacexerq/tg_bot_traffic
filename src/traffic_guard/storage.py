from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(slots=True)
class State:
    period: str
    accumulated_bytes: int = 0
    last_total_bytes: int | None = None
    notified_thresholds: list[int] = field(default_factory=list)
    last_daily_report_date: str | None = None
    telegram_update_offset: int = 0


def load_state(path: Path, period: str) -> State:
    if not path.exists():
        return State(period=period)

    data = json.loads(path.read_text(encoding="utf-8"))
    saved_period = data.get("period")
    if saved_period != period:
        return State(
            period=period,
            telegram_update_offset=int(data.get("telegram_update_offset", 0)),
        )

    return State(
        period=saved_period,
        accumulated_bytes=int(data.get("accumulated_bytes", 0)),
        last_total_bytes=data.get("last_total_bytes"),
        notified_thresholds=[int(value) for value in data.get("notified_thresholds", [])],
        last_daily_report_date=data.get("last_daily_report_date"),
        telegram_update_offset=int(data.get("telegram_update_offset", 0)),
    )


def save_state(path: Path, state: State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")
