from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class ControlState:
    telegram_update_offset: int = 0


def load_control_state(path: Path) -> ControlState:
    if not path.exists():
        return ControlState()

    data = json.loads(path.read_text(encoding="utf-8"))
    return ControlState(
        telegram_update_offset=int(data.get("telegram_update_offset", 0)),
    )


def save_control_state(path: Path, state: ControlState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")
