"""Metric card widget — label + value + colored bar + sparkline."""

from __future__ import annotations

from rich.text import Text

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, Sparkline
from textual.reactive import reactive


class MetricCard(Vertical):
    """A card showing a metric with label, value, bar, and optional sparkline."""

    DEFAULT_CSS = """
    MetricCard {
        height: auto;
        min-height: 5;
        padding: 0 1;
        border: round $panel;
        background: $surface;
        margin: 0 1 1 0;
    }
    MetricCard .mc-title {
        color: $primary;
        text-style: bold;
        height: 1;
    }
    MetricCard .mc-value {
        color: $foreground;
        height: 1;
    }
    MetricCard .mc-bar {
        height: 1;
    }
    MetricCard Sparkline {
        height: 2;
        margin-top: 1;
    }
    """

    value: reactive[float] = reactive(0.0)
    label_text: reactive[str] = reactive("")
    detail_text: reactive[str] = reactive("")

    def __init__(
        self,
        title: str,
        value: float = 0.0,
        detail: str = "",
        show_sparkline: bool = True,
        *,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._title = title
        self.value = value
        self.detail_text = detail
        self._show_sparkline = show_sparkline
        self._sparkline_data: list[float] = []

    def compose(self) -> ComposeResult:
        yield Static(self._title, classes="mc-title")
        yield Static("", classes="mc-value", id="mc-val")
        yield Static("", classes="mc-bar", id="mc-bar")
        if self._show_sparkline:
            yield Sparkline([], id="mc-spark")

    def on_mount(self) -> None:
        self._update_display()

    def _update_display(self) -> None:
        pct = max(0.0, min(100.0, self.value))
        width = max(self.size.width - 6, 10)
        filled = int(width * pct / 100)
        empty = width - filled

        if pct >= 90:
            color = "red"
        elif pct >= 70:
            color = "yellow"
        else:
            color = "green"

        bar = Text()
        bar.append("█" * filled, style=color)
        bar.append("░" * empty, style="dim")
        bar.append(f" {pct:.0f}%")

        try:
            self.query_one("#mc-val", Static).update(self.detail_text)
            self.query_one("#mc-bar", Static).update(bar)
        except Exception:
            pass

    def update_sparkline(self, data: list[float]) -> None:
        self._sparkline_data = data
        if self._show_sparkline:
            try:
                spark = self.query_one("#mc-spark", Sparkline)
                spark.data = data
            except Exception:
                pass

    def watch_value(self) -> None:
        self._update_display()

    def watch_detail_text(self) -> None:
        self._update_display()
