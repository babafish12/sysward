"""Root detection and privilege escalation helpers."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def is_root() -> bool:
    return os.geteuid() == 0


def can_write_sysfs(path: str | Path) -> bool:
    """Check if we can write to a sysfs file."""
    try:
        p = Path(path)
        return p.exists() and os.access(p, os.W_OK)
    except OSError:
        return False


def write_sysfs(path: str | Path, value: str) -> bool:
    """Write a value to sysfs. Returns True on success."""
    try:
        Path(path).write_text(value)
        return True
    except (PermissionError, OSError):
        return False


def write_sysfs_privileged(path: str | Path, value: str) -> bool:
    """Write to sysfs with pkexec fallback if needed."""
    if write_sysfs(path, value):
        return True

    # pkexec fallback
    try:
        result = subprocess.run(
            ["pkexec", "tee", str(path)],
            input=value, capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
