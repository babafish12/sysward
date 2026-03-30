"""Session logger — JSONL metric logging with rotation."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class SessionLogger:
    """Logs metrics to JSONL files with rotation."""

    def __init__(
        self,
        log_dir: Path | str = "~/.local/share/sysward/logs",
        max_size_mb: float = 5.0,
        max_files: int = 10,
        interval: float = 5.0,
    ) -> None:
        self._log_dir = Path(log_dir).expanduser()
        self._max_size = int(max_size_mb * 1_048_576)
        self._max_files = max_files
        self._interval = interval
        self._file: Any = None
        self._file_path: Path | None = None
        self._last_write = 0.0
        self._enabled = False

    def start(self) -> None:
        self._enabled = True
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._open_new_file()

    def stop(self) -> None:
        self._enabled = False
        if self._file:
            self._file.close()
            self._file = None

    def append(self, metrics: dict[str, Any]) -> None:
        if not self._enabled or not self._file:
            return
        now = time.time()
        if now - self._last_write < self._interval:
            return
        self._last_write = now

        entry = {
            "ts": datetime.fromtimestamp(now).isoformat(),
            **{k: v for k, v in metrics.items() if isinstance(v, (int, float, str, bool, dict))},
        }
        try:
            self._file.write(json.dumps(entry, default=str) + "\n")
            self._file.flush()
            self._maybe_rotate()
        except OSError:
            pass

    def _open_new_file(self) -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._file_path = self._log_dir / f"session-{ts}.jsonl"
        self._file = open(self._file_path, "a")

    def _maybe_rotate(self) -> None:
        if not self._file_path or not self._file_path.exists():
            return
        if self._file_path.stat().st_size < self._max_size:
            return
        self._file.close()
        self._open_new_file()
        self._cleanup_old()

    def _cleanup_old(self) -> None:
        logs = sorted(self._log_dir.glob("session-*.jsonl"))
        while len(logs) > self._max_files:
            try:
                logs[0].unlink()
                logs.pop(0)
            except OSError:
                break
