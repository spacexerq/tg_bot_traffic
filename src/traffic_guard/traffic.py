from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PROC_NET_DEV = Path("/proc/net/dev")


@dataclass(slots=True)
class InterfaceStats:
    name: str
    rx_bytes: int
    tx_bytes: int

    @property
    def total_bytes(self) -> int:
        return self.rx_bytes + self.tx_bytes


@dataclass(slots=True)
class TrafficSnapshot:
    total_bytes: int
    interfaces: list[str]


def current_period_utc(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.strftime("%Y-%m")


def read_all_interface_stats() -> list[InterfaceStats]:
    if not PROC_NET_DEV.exists():
        raise FileNotFoundError("/proc/net/dev is not available. This service supports Linux only.")

    interface_stats: list[InterfaceStats] = []
    raw_lines = PROC_NET_DEV.read_text(encoding="utf-8").splitlines()[2:]
    for line in raw_lines:
        name_part, stats_part = line.split(":", maxsplit=1)
        interface = name_part.strip()
        columns = stats_part.split()
        interface_stats.append(
            InterfaceStats(
                name=interface,
                rx_bytes=int(columns[0]),
                tx_bytes=int(columns[8]),
            )
        )

    return interface_stats


def read_traffic_snapshot(include: list[str], exclude: list[str]) -> TrafficSnapshot:
    chosen_interfaces: list[str] = []
    total_bytes = 0
    excluded_prefixes = tuple(exclude)

    for stats in read_all_interface_stats():
        interface = stats.name
        if include and interface not in include:
            continue
        if interface in exclude or interface.startswith(excluded_prefixes):
            continue

        total_bytes += stats.total_bytes
        chosen_interfaces.append(interface)

    if not chosen_interfaces:
        raise RuntimeError("No network interfaces selected. Adjust TG_INTERFACE_INCLUDE or TG_INTERFACE_EXCLUDE.")

    return TrafficSnapshot(total_bytes=total_bytes, interfaces=chosen_interfaces)
