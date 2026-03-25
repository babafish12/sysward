"""CPU collector — /proc/stat, sysfs freq/governor/temp."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sysward.collectors.base import BaseCollector

_PROC_STAT = Path("/proc/stat")
_CPU_BASE = Path("/sys/devices/system/cpu")
_PSTATE = _CPU_BASE / "intel_pstate"


class CPUCollector(BaseCollector):
    def __init__(self) -> None:
        self._prev_times: dict[str, tuple[int, int]] = {}  # cpu_id -> (busy, total)

    def is_available(self) -> bool:
        return _PROC_STAT.exists()

    def collect(self) -> dict[str, Any]:
        data: dict[str, Any] = {}

        # Per-CPU usage from /proc/stat
        stat_lines = _PROC_STAT.read_text().splitlines()
        usages: list[float] = []
        total_usage = 0.0

        for line in stat_lines:
            if not line.startswith("cpu"):
                continue
            parts = line.split()
            cpu_id = parts[0]
            times = [int(x) for x in parts[1:]]
            # user, nice, system, idle, iowait, irq, softirq, steal
            idle = times[3] + (times[4] if len(times) > 4 else 0)
            total = sum(times)
            busy = total - idle

            if cpu_id in self._prev_times:
                prev_busy, prev_total = self._prev_times[cpu_id]
                d_busy = busy - prev_busy
                d_total = total - prev_total
                usage = (d_busy / d_total * 100) if d_total > 0 else 0.0
            else:
                usage = 0.0

            self._prev_times[cpu_id] = (busy, total)

            if cpu_id == "cpu":
                total_usage = usage
            else:
                usages.append(usage)

        data["usage"] = total_usage
        data["per_core_usage"] = usages
        data["core_count"] = len(usages)

        # Frequencies and governor from sysfs
        freqs: list[float] = []
        governors: list[str] = []
        for i in range(len(usages)):
            cpu_dir = _CPU_BASE / f"cpu{i}" / "cpufreq"
            freq_file = cpu_dir / "scaling_cur_freq"
            gov_file = cpu_dir / "scaling_governor"
            if freq_file.exists():
                try:
                    freqs.append(int(freq_file.read_text().strip()) / 1000)  # MHz
                except (ValueError, PermissionError):
                    freqs.append(0.0)
            if gov_file.exists():
                try:
                    governors.append(gov_file.read_text().strip())
                except (ValueError, PermissionError):
                    governors.append("unknown")

        data["frequencies"] = freqs
        data["governors"] = governors
        data["governor"] = governors[0] if governors else "unknown"

        # Average and max frequency
        if freqs:
            data["freq_avg"] = sum(freqs) / len(freqs)
            data["freq_max"] = max(freqs)
        else:
            data["freq_avg"] = 0.0
            data["freq_max"] = 0.0

        # Max frequency capability
        max_freq_file = _CPU_BASE / "cpu0" / "cpufreq" / "scaling_max_freq"
        if max_freq_file.exists():
            try:
                data["freq_max_capable"] = int(max_freq_file.read_text().strip()) / 1000
            except (ValueError, PermissionError):
                data["freq_max_capable"] = 0.0
        else:
            data["freq_max_capable"] = 0.0

        # Turbo boost state (intel_pstate)
        no_turbo = _PSTATE / "no_turbo"
        if no_turbo.exists():
            try:
                data["turbo"] = int(no_turbo.read_text().strip()) == 0  # inverted!
            except (ValueError, PermissionError):
                data["turbo"] = None
        else:
            data["turbo"] = None

        # EPP
        epp_file = _CPU_BASE / "cpu0" / "cpufreq" / "energy_performance_preference"
        if epp_file.exists():
            try:
                data["epp"] = epp_file.read_text().strip()
            except (ValueError, PermissionError):
                data["epp"] = "unknown"
        else:
            data["epp"] = "unknown"

        return data
