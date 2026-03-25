"""Systemd service collector — systemctl wrapper."""

from __future__ import annotations

import subprocess
from typing import Any

from sysward.collectors.base import BaseCollector


class SystemdCollector(BaseCollector):
    def is_available(self) -> bool:
        try:
            subprocess.run(
                ["systemctl", "--version"],
                capture_output=True, timeout=2,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def collect(self) -> dict[str, Any]:
        services = self._list_services()
        return {"services": services, "total": len(services)}

    def _list_services(self) -> list[dict[str, str]]:
        services: list[dict[str, str]] = []
        try:
            result = subprocess.run(
                [
                    "systemctl", "list-units",
                    "--type=service",
                    "--no-pager",
                    "--no-legend",
                    "--plain",
                ],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                parts = line.split(None, 4)
                if len(parts) < 4:
                    continue
                unit = parts[0]
                load = parts[1]
                active = parts[2]
                sub = parts[3]
                desc = parts[4] if len(parts) > 4 else ""
                services.append({
                    "unit": unit,
                    "load": load,
                    "active": active,
                    "sub": sub,
                    "description": desc,
                })
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return services
