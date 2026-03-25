"""Memory collector — /proc/meminfo + zram stats."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sysward.collectors.base import BaseCollector

_MEMINFO = Path("/proc/meminfo")
_ZRAM_BASE = Path("/sys/block")


class MemoryCollector(BaseCollector):
    def is_available(self) -> bool:
        return _MEMINFO.exists()

    def collect(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        info = self._parse_meminfo()

        total = info.get("MemTotal", 0)
        available = info.get("MemAvailable", 0)
        used = total - available
        buffers = info.get("Buffers", 0)
        cached = info.get("Cached", 0)
        sreclaimable = info.get("SReclaimable", 0)

        data["total"] = total
        data["available"] = available
        data["used"] = used
        data["buffers"] = buffers
        data["cached"] = cached + sreclaimable
        data["usage_percent"] = (used / total * 100) if total > 0 else 0.0

        # Swap
        swap_total = info.get("SwapTotal", 0)
        swap_free = info.get("SwapFree", 0)
        swap_used = swap_total - swap_free

        data["swap_total"] = swap_total
        data["swap_used"] = swap_used
        data["swap_free"] = swap_free
        data["swap_percent"] = (swap_used / swap_total * 100) if swap_total > 0 else 0.0

        # zram stats
        zram_data = self._collect_zram()
        data.update(zram_data)

        return data

    def _parse_meminfo(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for line in _MEMINFO.read_text().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                key = parts[0].rstrip(":")
                value = int(parts[1]) * 1024  # kB -> bytes
                result[key] = value
        return result

    def _collect_zram(self) -> dict[str, Any]:
        data: dict[str, Any] = {"zram_devices": []}
        for entry in sorted(_ZRAM_BASE.iterdir()):
            if not entry.name.startswith("zram"):
                continue
            disksize = entry / "disksize"
            mm_stat = entry / "mm_stat"
            if disksize.exists():
                try:
                    size = int(disksize.read_text().strip())
                    compr_size = 0
                    orig_size = 0
                    if mm_stat.exists():
                        parts = mm_stat.read_text().strip().split()
                        if len(parts) >= 2:
                            orig_size = int(parts[0])
                            compr_size = int(parts[1])
                    data["zram_devices"].append({
                        "name": entry.name,
                        "disksize": size,
                        "orig_size": orig_size,
                        "compr_size": compr_size,
                    })
                except (ValueError, PermissionError):
                    pass
        return data
