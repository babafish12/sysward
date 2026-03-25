"""Base collector abstract class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseCollector(ABC):
    """Abstract base for all hardware/system collectors."""

    @abstractmethod
    def collect(self) -> dict[str, Any]:
        """Collect metrics. Returns a dict of metric_name -> value."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the hardware/subsystem this collector targets exists."""
