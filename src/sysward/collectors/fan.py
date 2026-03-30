"""Fan collector — all fan speeds + ThinkPad ACPI fan info."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sysward.collectors.base import BaseCollector

_HWMON_BASE = Path("/sys/class/hwmon")
_TP_FAN = Path("/proc/acpi/ibm/fan")


class FanCollector(BaseCollector):
    def __init__(self) -> None:
        self._hwmon_map: dict[str, Path] = {}
        self._tp_fan_control_available = False

    def is_available(self) -> bool:
        return _HWMON_BASE.exists() or _TP_FAN.exists()

    def collect(self) -> dict[str, Any]:
        self._scan_hwmon()
        data: dict[str, Any] = {"fans": {}, "thinkpad": None}

        # Collect all fans from all hwmon devices
        for name, path in self._hwmon_map.items():
            fans = self._read_fans(path)
            for label, rpm in fans.items():
                key = f"{name}/{label}"
                data["fans"][key] = rpm

        # ThinkPad ACPI
        if _TP_FAN.exists():
            tp = self._read_thinkpad_fan()
            data["thinkpad"] = tp
            # Also add to fans dict for unified display
            if tp.get("speed"):
                data["fans"]["thinkpad/fan1"] = tp["speed"]

        return data

    def _scan_hwmon(self) -> None:
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

    def _read_fans(self, path: Path) -> dict[str, int]:
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

    def _read_thinkpad_fan(self) -> dict[str, Any]:
        """Parse /proc/acpi/ibm/fan output."""
        result: dict[str, Any] = {"available": True, "control_enabled": False}
        try:
            content = _TP_FAN.read_text()
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("status:"):
                    result["status"] = line.split(":", 1)[1].strip()
                elif line.startswith("speed:"):
                    try:
                        result["speed"] = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        result["speed"] = 0
                elif line.startswith("level:"):
                    result["level"] = line.split(":", 1)[1].strip()
                elif "commands:" in line:
                    # If "level <n>" commands are available, fan_control=1 is set
                    if "level" in line:
                        result["control_enabled"] = True
        except (PermissionError, OSError):
            result["available"] = False
        return result
