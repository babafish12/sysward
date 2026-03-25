"""Battery collector — /sys/class/power_supply/BAT0/."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sysward.collectors.base import BaseCollector

_PS_BASE = Path("/sys/class/power_supply")


class BatteryCollector(BaseCollector):
    def __init__(self) -> None:
        self._bat_path: Path | None = None

    def is_available(self) -> bool:
        if not _PS_BASE.exists():
            return False
        for entry in sorted(_PS_BASE.iterdir()):
            if entry.name.startswith("BAT"):
                self._bat_path = entry
                return True
        return False

    def collect(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if not self._bat_path:
            return data

        def _read(name: str) -> str | None:
            p = self._bat_path / name
            if p.exists():
                try:
                    return p.read_text().strip()
                except (PermissionError, OSError):
                    pass
            return None

        data["status"] = _read("status") or "Unknown"

        capacity = _read("capacity")
        data["capacity"] = int(capacity) if capacity else 0

        energy_now = _read("energy_now")
        energy_full = _read("energy_full")
        energy_full_design = _read("energy_full_design")
        power_now = _read("power_now")

        if energy_now:
            data["energy_now"] = int(energy_now) / 1_000_000  # uWh -> Wh
        if energy_full:
            data["energy_full"] = int(energy_full) / 1_000_000
        if energy_full_design:
            data["energy_full_design"] = int(energy_full_design) / 1_000_000
        if power_now:
            data["power_draw"] = int(power_now) / 1_000_000  # uW -> W

        # Health percentage
        if energy_full and energy_full_design:
            ef = int(energy_full)
            efd = int(energy_full_design)
            data["health"] = (ef / efd * 100) if efd > 0 else 0.0

        return data
