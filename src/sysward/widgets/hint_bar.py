"""Keybinding hint bar widget."""

from __future__ import annotations

from textual.widgets import Static

from sysward.theme import get_color


class HintBar(Static):
    """Compact keybinding hint bar at the bottom."""

    DEFAULT_CSS = """
    HintBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, hints: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._hints = hints

    def on_mount(self) -> None:
        self.refresh_hints()

    def refresh_hints(self, hints: str | None = None) -> None:
        if hints is not None:
            self._hints = hints
        accent = get_color(self.app.theme, "accent")
        self.update(self._hints.replace("[k]", f"[bold {accent}]").replace("[/k]", "[/]"))

    def set_hints(self, hints: str) -> None:
        self._hints = hints
        self.refresh_hints()
