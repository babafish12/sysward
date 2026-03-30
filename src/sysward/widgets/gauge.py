"""Horizontal gauge widget with color-coded fill and label."""

from __future__ import annotations

from rich.text import Text

from textual.widgets import Static
from textual.reactive import reactive


class Gauge(Static):
    """A horizontal bar gauge showing a percentage value with color thresholds."""

    DEFAULT_CSS = """
    Gauge {
        height: 1;
        width: 1fr;
    }
    """

    value: reactive[float] = reactive(0.0)
    label: reactive[str] = reactive("")

    def __init__(
        self,
        label: str = "",
        value: float = 0.0,
        *,
        warn_threshold: float = 70.0,
        crit_threshold: float = 90.0,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.label = label
        self.value = value
        self._warn = warn_threshold
        self._crit = crit_threshold

    def render(self) -> Text:
        pct = max(0.0, min(100.0, self.value))
        width = max(self.size.width - len(self.label) - 8, 10)
        filled = int(width * pct / 100)
        empty = width - filled

        if pct >= self._crit:
            color = "red"
        elif pct >= self._warn:
            color = "yellow"
        else:
            color = "green"

        bar = Text()
        bar.append(f"{self.label} ", style="bold")
        bar.append("\u2593" * filled, style=color)
        bar.append("\u2591" * empty, style="dim")
        bar.append(f" {pct:5.1f}%", style=color + " bold")
        return bar

    def watch_value(self) -> None:
        self.refresh()

    def watch_label(self) -> None:
        self.refresh()
