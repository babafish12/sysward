"""ThinkPad fan control with safety guardrails."""

from __future__ import annotations

import atexit
import os
import signal
from pathlib import Path
from typing import Any

from sysward.services.privilege import write_proc_privileged

_TP_FAN = Path("/proc/acpi/ibm/fan")
_LOCK_FILE = Path("/tmp/sysward-fan.lock")
_VALID_LEVELS = {"auto", "full-speed", "1", "2", "3", "4", "5", "6", "7"}


class ThinkPadFanControl:
    """Controls ThinkPad fan via /proc/acpi/ibm/fan with safety guardrails."""

    def __init__(self) -> None:
        self._manual_mode = False
        self._original_handlers: dict[int, Any] = {}

    @property
    def available(self) -> bool:
        return _TP_FAN.exists()

    @property
    def control_enabled(self) -> bool:
        """Check if fan_control=1 module parameter is set."""
        if not self.available:
            return False
        try:
            content = _TP_FAN.read_text()
            for line in content.splitlines():
                if "commands:" in line and "level" in line:
                    return True
        except (PermissionError, OSError):
            pass
        return False

    def set_level(self, level: str) -> tuple[bool, str]:
        """Set fan level. Returns (success, message)."""
        if not self.available:
            return False, "ThinkPad fan interface not available"
        if not self.control_enabled:
            return False, "Fan control not enabled (set fan_control=1 in thinkpad_acpi)"
        if level == "0":
            return False, "Level 0 (fan off) is rejected for safety"
        if level not in _VALID_LEVELS:
            return False, f"Invalid level: {level}. Valid: {', '.join(sorted(_VALID_LEVELS))}"

        value = f"level {level}"
        try:
            ok = write_proc_privileged(str(_TP_FAN), value)
            if ok:
                if level != "auto":
                    self._enter_manual_mode()
                else:
                    self._exit_manual_mode()
                return True, f"Fan level set to {level}"
            return False, "Failed to write fan level (pkexec denied?)"
        except ValueError as e:
            return False, str(e)

    def reset_to_auto(self) -> None:
        """Unconditionally reset fan to auto mode."""
        if not self.available:
            return
        try:
            write_proc_privileged(str(_TP_FAN), "level auto")
        except (ValueError, OSError):
            pass
        self._cleanup_lock()

    def check_safety(self, cpu_temp: float, safety_limit: float = 90.0) -> bool:
        """Force full-speed if temperature exceeds safety limit. Returns True if override triggered."""
        if cpu_temp >= safety_limit and self._manual_mode:
            try:
                write_proc_privileged(str(_TP_FAN), "level full-speed")
            except (ValueError, OSError):
                pass
            return True
        return False

    def check_stale_lock(self) -> None:
        """On startup, check for stale lock and reset fan if found."""
        if _LOCK_FILE.exists():
            try:
                pid = int(_LOCK_FILE.read_text().strip())
                # Check if process is still running
                try:
                    os.kill(pid, 0)
                except OSError:
                    # Process dead, stale lock
                    self.reset_to_auto()
            except (ValueError, OSError):
                self._cleanup_lock()

    def _enter_manual_mode(self) -> None:
        if self._manual_mode:
            return
        self._manual_mode = True
        # Write lock file
        try:
            _LOCK_FILE.write_text(str(os.getpid()))
        except OSError:
            pass
        # Register cleanup handlers
        atexit.register(self.reset_to_auto)
        for sig in (signal.SIGTERM, signal.SIGHUP):
            try:
                self._original_handlers[sig] = signal.getsignal(sig)
                signal.signal(sig, self._signal_handler)
            except (OSError, ValueError):
                pass

    def _exit_manual_mode(self) -> None:
        self._manual_mode = False
        self._cleanup_lock()

    def _cleanup_lock(self) -> None:
        try:
            _LOCK_FILE.unlink(missing_ok=True)
        except OSError:
            pass

    def _signal_handler(self, signum: int, frame: Any) -> None:
        self.reset_to_auto()
        # Call original handler
        orig = self._original_handlers.get(signum, signal.SIG_DFL)
        if callable(orig):
            orig(signum, frame)
        elif orig == signal.SIG_DFL:
            signal.signal(signum, signal.SIG_DFL)
            os.kill(os.getpid(), signum)
