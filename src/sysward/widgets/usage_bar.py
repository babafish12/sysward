"""Colored usage bar widget — green/yellow/red based on percentage."""

from __future__ import annotations

from rich.text import Text

from textual.widgets import Static
from textual.reactive import reactive


class UsageBar(Static):
    """A colored progress bar that changes color based on usage level."""

    DEFAULT_CSS = """
    UsageBar {
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
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.label = label
        self.value = value

    def render(self) -> Text:
        width = self.size.width - len(self.label) - 10
        if width < 4:
            width = 4

        pct = max(0.0, min(100.0, self.value))
        filled = int(width * pct / 100)
        empty = width - filled

        if pct >= 90:
            color = "red"
        elif pct >= 70:
            color = "yellow"
        else:
            color = "green"

        text = Text()
        text.append(f"{self.label} ")
        text.append("█" * filled, style=color)
        text.append("░" * empty, style="dim")
        text.append(f" {pct:5.1f}%")
        return text

    def watch_value(self) -> None:
        self.refresh()

    def watch_label(self) -> None:
        self.refresh()
