"""Systemd services screen tab."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Input

from sysward.widgets.service_table import ServiceTable


class SystemdScreen(Vertical):
    """Systemd service management tab content."""

    DEFAULT_CSS = """
    SystemdScreen {
        height: 1fr;
        padding: 1;
    }
    SystemdScreen #svc-header {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    SystemdScreen #svc-filter {
        height: 3;
        margin: 0 1;
    }
    SystemdScreen ServiceTable {
        margin: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._services: list[dict[str, str]] = []
        self._filter_visible = False

    def compose(self) -> ComposeResult:
        yield Static("", id="svc-header")
        yield Horizontal(
            Input(placeholder="Filter services...", id="svc-filter-input"),
            id="svc-filter",
        )
        yield ServiceTable(id="svc-table")

    def on_mount(self) -> None:
        self.query_one("#svc-filter").display = False

    def update_metrics(self, metrics: dict[str, Any], history: dict) -> None:
        svc_data = metrics.get("systemd", {})
        self._services = svc_data.get("services", [])
        total = svc_data.get("total", 0)

        try:
            self.query_one("#svc-header", Static).update(
                f"Services: {total} | [/] Filter"
            )
        except Exception:
            pass

        table = self.query_one("#svc-table", ServiceTable)
        table.load_services(self._services)

    def toggle_filter(self) -> None:
        self._filter_visible = not self._filter_visible
        filter_box = self.query_one("#svc-filter")
        filter_box.display = self._filter_visible
        if self._filter_visible:
            self.query_one("#svc-filter-input", Input).focus()
        else:
            self.query_one("#svc-filter-input", Input).value = ""
            self.query_one("#svc-table", ServiceTable).set_filter("")
            self.query_one("#svc-table", ServiceTable).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "svc-filter-input":
            table = self.query_one("#svc-table", ServiceTable)
            table.set_filter(event.value)
            table.load_services(self._services)

    def get_selected_unit(self) -> str | None:
        return self.query_one("#svc-table", ServiceTable).get_selected_unit()
