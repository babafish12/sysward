"""Network collector — /proc/net/dev."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sysward.collectors.base import BaseCollector

_NET_DEV = Path("/proc/net/dev")


class NetworkCollector(BaseCollector):
    def __init__(self) -> None:
        self._prev_stats: dict[str, tuple[int, int]] = {}  # iface -> (rx_bytes, tx_bytes)

    def is_available(self) -> bool:
        return _NET_DEV.exists()

    def collect(self) -> dict[str, Any]:
        data: dict[str, Any] = {"interfaces": []}

        lines = _NET_DEV.read_text().splitlines()[2:]  # skip headers
        for line in lines:
            parts = line.split()
            if len(parts) < 10:
                continue
            iface = parts[0].rstrip(":")
            if iface == "lo":
                continue

            rx_bytes = int(parts[1])
            tx_bytes = int(parts[9])

            rx_rate = 0.0
            tx_rate = 0.0
            if iface in self._prev_stats:
                prev_rx, prev_tx = self._prev_stats[iface]
                rx_rate = float(rx_bytes - prev_rx)
                tx_rate = float(tx_bytes - prev_tx)

            self._prev_stats[iface] = (rx_bytes, tx_bytes)

            # Check if interface is up
            operstate_file = Path(f"/sys/class/net/{iface}/operstate")
            operstate = "unknown"
            if operstate_file.exists():
                try:
                    operstate = operstate_file.read_text().strip()
                except (PermissionError, OSError):
                    pass

            data["interfaces"].append({
                "name": iface,
                "rx_bytes": rx_bytes,
                "tx_bytes": tx_bytes,
                "rx_rate": rx_rate,
                "tx_rate": tx_rate,
                "state": operstate,
            })

        return data
