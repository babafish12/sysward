"""Ring buffer for metric history."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class RingBuffer:
    """Deque-based ring buffer for time-series data."""

    maxlen: int = 3600  # 1 hour at 1s intervals
    _data: deque[float] = field(default_factory=lambda: deque(maxlen=3600))

    def __post_init__(self) -> None:
        self._data = deque(maxlen=self.maxlen)

    def push(self, value: float) -> None:
        self._data.append(value)

    @property
    def values(self) -> list[float]:
        return list(self._data)

    def last_n(self, n: int) -> list[float]:
        """Return last n values."""
        data = self.values
        return data[-n:] if len(data) >= n else data

    @property
    def latest(self) -> float | None:
        return self._data[-1] if self._data else None

    def __len__(self) -> int:
        return len(self._data)
