"""Process manager — SIGSTOP/SIGTERM + blacklist enforcement."""

from __future__ import annotations

import os
import signal
from pathlib import Path


class ProcessManager:
    def kill_process(self, pid: int) -> tuple[bool, str]:
        """Send SIGTERM to a process."""
        try:
            os.kill(pid, signal.SIGTERM)
            return True, f"Sent SIGTERM to PID {pid}"
        except ProcessLookupError:
            return False, f"PID {pid} not found"
        except PermissionError:
            return False, f"Permission denied for PID {pid} (try running as root)"

    def stop_process(self, pid: int) -> tuple[bool, str]:
        """Send SIGSTOP to pause a process."""
        try:
            os.kill(pid, signal.SIGSTOP)
            return True, f"Stopped PID {pid}"
        except ProcessLookupError:
            return False, f"PID {pid} not found"
        except PermissionError:
            return False, f"Permission denied for PID {pid}"

    def resume_process(self, pid: int) -> tuple[bool, str]:
        """Send SIGCONT to resume a process."""
        try:
            os.kill(pid, signal.SIGCONT)
            return True, f"Resumed PID {pid}"
        except ProcessLookupError:
            return False, f"PID {pid} not found"
        except PermissionError:
            return False, f"Permission denied for PID {pid}"

    def enforce_blacklist(self, blacklist: dict[str, str]) -> list[str]:
        """Scan running processes and apply blacklist rules. Returns list of actions taken."""
        if not blacklist:
            return []

        actions: list[str] = []
        proc = Path("/proc")

        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            comm_file = entry / "comm"
            try:
                comm = comm_file.read_text().strip()
            except (PermissionError, FileNotFoundError, OSError):
                continue

            if comm in blacklist:
                action = blacklist[comm]
                if action == "stop":
                    ok, msg = self.stop_process(pid)
                elif action == "kill":
                    ok, msg = self.kill_process(pid)
                else:
                    continue
                if ok:
                    actions.append(f"{action}: {comm} (PID {pid})")

        return actions
