"""Process screen tab — sortable/filterable process table."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Input

from sysward.widgets.process_table import ProcessTable


class ProcessScreen(Vertical):
    """Process management tab content."""

    DEFAULT_CSS = """
    ProcessScreen {
        height: 1fr;
        padding: 1;
    }
    ProcessScreen #proc-header {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    ProcessScreen #proc-filter {
        height: 3;
        margin: 0 1;
    }
    ProcessScreen #proc-filter Input {
        width: 1fr;
    }
    ProcessScreen ProcessTable {
        margin: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._processes: list[dict[str, Any]] = []
        self._filter_visible = False

    def compose(self) -> ComposeResult:
        yield Static("", id="proc-header")
        yield Horizontal(
            Input(placeholder="Filter processes...", id="proc-filter-input"),
            id="proc-filter",
        )
        yield ProcessTable(id="proc-table")

    def on_mount(self) -> None:
        self.query_one("#proc-filter").display = False

    def update_metrics(self, metrics: dict[str, Any], history: dict) -> None:
        proc_data = metrics.get("process", {})
        self._processes = proc_data.get("processes", [])
        total = proc_data.get("total", 0)

        try:
            self.query_one("#proc-header", Static).update(
                f"Processes: {total} | k=Kill  s=Stop  r=Resume  b=Blacklist  /=Filter"
            )
        except Exception:
            pass

        table = self.query_one("#proc-table", ProcessTable)
        table.load_processes(self._processes)

    def toggle_filter(self) -> None:
        self._filter_visible = not self._filter_visible
        filter_box = self.query_one("#proc-filter")
        filter_box.display = self._filter_visible
        if self._filter_visible:
            self.query_one("#proc-filter-input", Input).focus()
        else:
            self.query_one("#proc-filter-input", Input).value = ""
            self.query_one("#proc-table", ProcessTable).set_filter("")
            self.query_one("#proc-table", ProcessTable).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "proc-filter-input":
            table = self.query_one("#proc-table", ProcessTable)
            table.set_filter(event.value)
            table.load_processes(self._processes)

    def get_selected_pid(self) -> int | None:
        return self.query_one("#proc-table", ProcessTable).get_selected_pid()
