"""GPU collector — Intel Iris Xe via sysfs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sysward.collectors.base import BaseCollector

_DRM_BASE = Path("/sys/class/drm")


class GPUCollector(BaseCollector):
    def __init__(self) -> None:
        self._card_path: Path | None = None

    def is_available(self) -> bool:
        # Find the Intel GPU card directory
        if not _DRM_BASE.exists():
            return False
        for entry in sorted(_DRM_BASE.iterdir()):
            if not entry.name.startswith("card") or "-" in entry.name:
                continue
            gt_freq = entry / "gt_cur_freq_mhz"
            if gt_freq.exists():
                self._card_path = entry
                return True
        return False

    def collect(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if not self._card_path:
            return data

        def _read_int(name: str) -> int | None:
            p = self._card_path / name
            if p.exists():
                try:
                    return int(p.read_text().strip())
                except (ValueError, PermissionError):
                    pass
            return None

        data["freq_cur"] = _read_int("gt_cur_freq_mhz") or 0
        data["freq_max"] = _read_int("gt_max_freq_mhz") or 0
        data["freq_min"] = _read_int("gt_min_freq_mhz") or 0
        data["freq_boost"] = _read_int("gt_boost_freq_mhz") or 0
        data["freq_act"] = _read_int("gt_act_freq_mhz") or 0

        # RC6 residency (power saving state)
        rc6_file = self._card_path / "gt" / "rc6_residency_ms"
        if not rc6_file.exists():
            # Try alternate path
            for p in self._card_path.glob("**/rc6_residency_ms"):
                rc6_file = p
                break

        if rc6_file.exists():
            try:
                data["rc6_residency_ms"] = int(rc6_file.read_text().strip())
            except (ValueError, PermissionError):
                data["rc6_residency_ms"] = None
        else:
            data["rc6_residency_ms"] = None

        return data
