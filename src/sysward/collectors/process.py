"""Process collector — /proc/[pid]/stat."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sysward.collectors.base import BaseCollector

_PROC = Path("/proc")
_CLK_TCK = os.sysconf("SC_CLK_TCK")
_PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")


class ProcessCollector(BaseCollector):
    def __init__(self) -> None:
        self._prev_times: dict[int, tuple[int, float]] = {}  # pid -> (cpu_ticks, timestamp)

    def is_available(self) -> bool:
        return _PROC.exists()

    def collect(self) -> dict[str, Any]:
        processes: list[dict[str, Any]] = []
        uptime = float(Path("/proc/uptime").read_text().split()[0])

        for entry in _PROC.iterdir():
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            try:
                proc = self._read_process(pid, uptime)
                if proc:
                    processes.append(proc)
            except (PermissionError, FileNotFoundError, ProcessLookupError, OSError):
                continue

        # Sort by CPU usage descending
        processes.sort(key=lambda p: p.get("cpu_percent", 0), reverse=True)

        return {"processes": processes, "total": len(processes)}

    def _read_process(self, pid: int, uptime: float) -> dict[str, Any] | None:
        stat_file = _PROC / str(pid) / "stat"
        if not stat_file.exists():
            return None

        stat_text = stat_file.read_text()
        # Parse carefully: comm can contain spaces and parentheses
        # Format: pid (comm) state ...
        lparen = stat_text.index("(")
        rparen = stat_text.rindex(")")
        comm = stat_text[lparen + 1 : rparen]
        fields = stat_text[rparen + 2 :].split()

        state = fields[0]
        ppid = int(fields[1])
        utime = int(fields[11])
        stime = int(fields[12])
        vsize = int(fields[20])  # bytes
        rss_pages = int(fields[21])
        rss = rss_pages * _PAGE_SIZE

        # CPU usage (delta-based)
        total_ticks = utime + stime
        cpu_percent = 0.0
        import time
        now = time.monotonic()
        if pid in self._prev_times:
            prev_ticks, prev_time = self._prev_times[pid]
            dt = now - prev_time
            if dt > 0:
                cpu_percent = ((total_ticks - prev_ticks) / _CLK_TCK) / dt * 100
        self._prev_times[pid] = (total_ticks, now)

        # Read cmdline for full command
        cmdline_file = _PROC / str(pid) / "cmdline"
        cmdline = comm
        try:
            raw = cmdline_file.read_bytes()
            if raw:
                cmdline = raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
        except (PermissionError, FileNotFoundError, OSError):
            pass

        # Read UID
        uid = -1
        status_file = _PROC / str(pid) / "status"
        try:
            for line in status_file.read_text().splitlines():
                if line.startswith("Uid:"):
                    uid = int(line.split()[1])
                    break
        except (PermissionError, FileNotFoundError, OSError):
            pass

        return {
            "pid": pid,
            "name": comm,
            "cmdline": cmdline,
            "state": state,
            "ppid": ppid,
            "cpu_percent": round(cpu_percent, 1),
            "rss": rss,
            "vsize": vsize,
            "uid": uid,
        }
