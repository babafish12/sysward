"""Root detection and privilege escalation helpers."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# Strict allowlists to prevent shell injection in pkexec calls.
_SAFE_PATH_RE = re.compile(r"^[a-zA-Z0-9_/.\-]+$")
_SAFE_VALUE_RE = re.compile(r"^[a-zA-Z0-9_ .\-]+$")


def _validate_path(path: str) -> bool:
    """Validate that a path contains only safe characters."""
    return bool(_SAFE_PATH_RE.match(str(path)))


def _validate_value(value: str) -> bool:
    """Validate that a value contains only safe characters."""
    return bool(_SAFE_VALUE_RE.match(value))


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


def write_sysfs_batch_privileged(writes: list[tuple[Path, str]]) -> bool:
    """Write multiple sysfs values in a single pkexec call.

    *writes* is a list of (path, value) tuples.
    All paths and values are validated against strict allowlists
    before being passed to the shell.
    Returns True if all writes succeeded.
    """
    if not writes:
        return True

    for path, val in writes:
        if not _validate_path(str(path)):
            raise ValueError(f"Unsafe path rejected: {path}")
        if not _validate_value(val):
            raise ValueError(f"Unsafe value rejected: {val}")

    parts = [f"echo '{val}' > '{path}'" for path, val in writes]
    combined = " && ".join(parts)
    try:
        result = subprocess.run(
            ["pkexec", "bash", "-c", combined],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def write_proc_privileged(path: str, value: str) -> bool:
    """Write a value to a /proc file via pkexec (for fan control etc.).

    Path must start with /proc/ or /sys/. Value is validated.
    """
    path_str = str(path)
    if not (path_str.startswith("/proc/") or path_str.startswith("/sys/")):
        raise ValueError(f"Path must start with /proc/ or /sys/: {path_str}")
    if not _validate_path(path_str):
        raise ValueError(f"Unsafe path rejected: {path_str}")
    if not _SAFE_VALUE_RE.match(value):
        raise ValueError(f"Unsafe value rejected: {value}")

    try:
        result = subprocess.run(
            ["pkexec", "bash", "-c", f"echo '{value}' > '{path_str}'"],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
