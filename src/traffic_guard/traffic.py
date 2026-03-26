from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PROC_NET_DEV = Path("/proc/net/dev")


@dataclass(slots=True)
class TrafficSnapshot:
    total_bytes: int
    interfaces: list[str]


def current_period_utc(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.strftime("%Y-%m")


def read_traffic_snapshot(include: list[str], exclude: list[str]) -> TrafficSnapshot:
    if not PROC_NET_DEV.exists():
        raise FileNotFoundError("/proc/net/dev is not available. This service supports Linux only.")

    chosen_interfaces: list[str] = []
    total_bytes = 0
    raw_lines = PROC_NET_DEV.read_text(encoding="utf-8").splitlines()[2:]
    excluded_prefixes = tuple(exclude)

    for line in raw_lines:
        name_part, stats_part = line.split(":", maxsplit=1)
        interface = name_part.strip()
        if include and interface not in include:
            continue
        if interface in exclude or interface.startswith(excluded_prefixes):
            continue

        columns = stats_part.split()
        rx_bytes = int(columns[0])
        tx_bytes = int(columns[8])
        total_bytes += rx_bytes + tx_bytes
        chosen_interfaces.append(interface)

    if not chosen_interfaces:
        raise RuntimeError("No network interfaces selected. Adjust TG_INTERFACE_INCLUDE or TG_INTERFACE_EXCLUDE.")

    return TrafficSnapshot(total_bytes=total_bytes, interfaces=chosen_interfaces)
