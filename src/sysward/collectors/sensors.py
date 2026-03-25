"""Generic hwmon sensor scanner — dynamic, never hardcodes indices."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sysward.collectors.base import BaseCollector

_HWMON_BASE = Path("/sys/class/hwmon")


class SensorsCollector(BaseCollector):
    def __init__(self) -> None:
        self._hwmon_map: dict[str, Path] = {}  # name -> path

    def is_available(self) -> bool:
        return _HWMON_BASE.exists() and any(_HWMON_BASE.iterdir())

    def collect(self) -> dict[str, Any]:
        self._scan_hwmon()
        data: dict[str, Any] = {}

        # CPU temperatures (coretemp)
        if "coretemp" in self._hwmon_map:
            data["cpu_temps"] = self._read_temps(self._hwmon_map["coretemp"])

        # NVMe temperatures
        if "nvme" in self._hwmon_map:
            data["nvme_temps"] = self._read_temps(self._hwmon_map["nvme"])

        # Thinkpad EC (fans, etc.)
        if "thinkpad" in self._hwmon_map:
            tp = self._hwmon_map["thinkpad"]
            data["thinkpad"] = {}
            fans = self._read_fans(tp)
            if fans:
                data["thinkpad"]["fans"] = fans
            temps = self._read_temps(tp)
            if temps:
                data["thinkpad"]["temps"] = temps

        # WiFi temps
        if "iwlwifi_1" in self._hwmon_map:
            data["wifi_temps"] = self._read_temps(self._hwmon_map["iwlwifi_1"])
        elif "iwlwifi" in self._hwmon_map:
            data["wifi_temps"] = self._read_temps(self._hwmon_map["iwlwifi"])

        # Package temp (shortcut for overview)
        cpu_temps = data.get("cpu_temps", {})
        if cpu_temps:
            # First entry is usually Package id 0
            first_label = next(iter(cpu_temps), None)
            if first_label:
                data["package_temp"] = cpu_temps[first_label]
            else:
                data["package_temp"] = 0
        else:
            data["package_temp"] = 0

        # Fan speed (shortcut)
        tp_fans = data.get("thinkpad", {}).get("fans", {})
        if tp_fans:
            data["fan_rpm"] = next(iter(tp_fans.values()), 0)
        else:
            data["fan_rpm"] = 0

        return data

    def _scan_hwmon(self) -> None:
        """Rescan hwmon devices by name — indices change on reboot."""
        self._hwmon_map.clear()
        if not _HWMON_BASE.exists():
            return
        for entry in _HWMON_BASE.iterdir():
            name_file = entry / "name"
            if name_file.exists():
                try:
                    name = name_file.read_text().strip()
                    self._hwmon_map[name] = entry
                except (PermissionError, OSError):
                    pass

    def _read_temps(self, path: Path) -> dict[str, float]:
        """Read all temp*_input files, keyed by label or index."""
        temps: dict[str, float] = {}
        for f in sorted(path.glob("temp*_input")):
            try:
                val = int(f.read_text().strip()) / 1000  # millidegrees -> C
                # Try to find label
                idx = f.name.replace("_input", "")
                label_file = path / f"{idx}_label"
                if label_file.exists():
                    label = label_file.read_text().strip()
                else:
                    label = idx
                temps[label] = val
            except (ValueError, PermissionError, OSError):
                pass
        return temps

    def _read_fans(self, path: Path) -> dict[str, int]:
        """Read all fan*_input files."""
        fans: dict[str, int] = {}
        for f in sorted(path.glob("fan*_input")):
            try:
                val = int(f.read_text().strip())
                idx = f.name.replace("_input", "")
                label_file = path / f"{idx}_label"
                if label_file.exists():
                    label = label_file.read_text().strip()
                else:
                    label = idx
                fans[label] = val
            except (ValueError, PermissionError, OSError):
                pass
        return fans
