"""Ring buffer for metric history."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class RingBuffer:
    """Deque-based ring buffer for time-series data with timestamps."""

    maxlen: int = 3600  # 1 hour at 1s intervals
    _data: deque[float] = field(default_factory=lambda: deque(maxlen=3600))
    _timestamps: deque[float] = field(default_factory=lambda: deque(maxlen=3600))

    def __post_init__(self) -> None:
        self._data = deque(maxlen=self.maxlen)
        self._timestamps = deque(maxlen=self.maxlen)

    def push(self, value: float, timestamp: float | None = None) -> None:
        self._data.append(value)
        self._timestamps.append(timestamp if timestamp is not None else time.time())

    @property
    def values(self) -> list[float]:
        return list(self._data)

    def last_n(self, n: int) -> list[float]:
        """Return last n values (backward compatible)."""
        data = self.values
        return data[-n:] if len(data) >= n else data

    def last_n_with_time(self, n: int) -> list[tuple[float, float]]:
        """Return last n (timestamp, value) pairs for chart rendering."""
        vals = list(self._data)
        ts = list(self._timestamps)
        paired = list(zip(ts, vals))
        return paired[-n:] if len(paired) >= n else paired

    @property
    def latest(self) -> float | None:
        return self._data[-1] if self._data else None

    def __len__(self) -> int:
        return len(self._data)
