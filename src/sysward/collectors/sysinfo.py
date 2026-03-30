"""System information collector — mostly static data, collected once."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from sysward.collectors.base import BaseCollector


class SysInfoCollector(BaseCollector):
    """Collects system information (kernel, CPU model, GPU, packages, etc.)."""

    def __init__(self) -> None:
        self._static_data: dict[str, Any] | None = None

    def is_available(self) -> bool:
        return Path("/proc/version").exists()

    def collect(self) -> dict[str, Any]:
        """Return static info (cached) + dynamic uptime."""
        if self._static_data is None:
            self._static_data = self._collect_static()
        # Only uptime changes at runtime
        self._static_data["uptime"] = self._read_uptime()
        return self._static_data

    def _collect_static(self) -> dict[str, Any]:
        data: dict[str, Any] = {}

        # Kernel
        try:
            data["kernel"] = Path("/proc/version").read_text().strip().split()[2]
        except (OSError, IndexError):
            data["kernel"] = "unknown"

        # Hostname
        try:
            data["hostname"] = Path("/etc/hostname").read_text().strip()
        except OSError:
            data["hostname"] = "unknown"

        # CPU model
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("model name"):
                    data["cpu_model"] = line.split(":", 1)[1].strip()
                    break
        except OSError:
            pass
        data.setdefault("cpu_model", "unknown")

        # Total RAM
        try:
            for line in Path("/proc/meminfo").read_text().splitlines():
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    data["ram_total_gb"] = round(kb / 1_048_576, 1)
                    break
        except (OSError, ValueError):
            pass
        data.setdefault("ram_total_gb", 0)

        # GPU
        try:
            lspci = subprocess.run(
                ["lspci"], capture_output=True, text=True, timeout=5
            )
            for line in lspci.stdout.splitlines():
                if "VGA" in line or "3D controller" in line:
                    data.setdefault("gpu_info", []).append(
                        line.split(": ", 1)[-1] if ": " in line else line
                    )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        data.setdefault("gpu_info", [])

        # Package count (cached, expensive)
        try:
            result = subprocess.run(
                ["pacman", "-Q"], capture_output=True, text=True, timeout=10
            )
            data["package_count"] = len(result.stdout.strip().splitlines())
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            data["package_count"] = 0

        # Boot time
        try:
            uptime_s = float(Path("/proc/uptime").read_text().split()[0])
            import time
            boot_ts = time.time() - uptime_s
            from datetime import datetime
            data["boot_time"] = datetime.fromtimestamp(boot_ts).strftime("%Y-%m-%d %H:%M:%S")
        except (OSError, ValueError):
            data["boot_time"] = "unknown"

        # Arch Linux release
        try:
            data["os_release"] = "Arch Linux"
            for line in Path("/etc/os-release").read_text().splitlines():
                if line.startswith("PRETTY_NAME="):
                    data["os_release"] = line.split("=", 1)[1].strip('"')
                    break
        except OSError:
            pass

        return data

    def _read_uptime(self) -> str:
        """Read uptime as human-readable string."""
        try:
            secs = float(Path("/proc/uptime").read_text().split()[0])
            days = int(secs // 86400)
            hours = int((secs % 86400) // 3600)
            mins = int((secs % 3600) // 60)
            parts = []
            if days:
                parts.append(f"{days}d")
            if hours:
                parts.append(f"{hours}h")
            parts.append(f"{mins}m")
            return " ".join(parts)
        except (OSError, ValueError):
            return "unknown"
