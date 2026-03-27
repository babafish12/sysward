"""Disk cleaner screen tab — scan and clean disk space."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, DataTable

from sysward.models.clean_item import ScanResult
from sysward.widgets.cleaner_table import CleanerTable


def _fmt_bytes(b: int) -> str:
    if b >= 1_073_741_824:
        return f"{b / 1_073_741_824:.1f} GiB"
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MiB"
    if b >= 1024:
        return f"{b / 1024:.0f} KiB"
    return f"{b} B"


class CleanerScreen(Vertical):
    """Disk cleaner tab content with category table and detail view."""

    DEFAULT_CSS = """
    CleanerScreen {
        height: 1fr;
        padding: 1;
    }
    CleanerScreen #clean-header {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    CleanerScreen #clean-summary {
        height: 1;
        padding: 0 1;
        color: $primary;
        text-style: bold;
    }
    CleanerScreen #clean-status {
        height: 1;
        padding: 0 1;
        color: $accent;
    }
    CleanerScreen CleanerTable {
        height: 1fr;
        margin: 0 1;
    }
    CleanerScreen #clean-detail-label {
        height: 1;
        padding: 0 1;
        margin-top: 1;
        color: $text-muted;
    }
    CleanerScreen #clean-detail {
        height: 10;
        margin: 0 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._scan_results: list[ScanResult] = []
        self._scanning = False

    def compose(self) -> ComposeResult:
        yield Static(
            "Disk Cleaner | s=Scan  Space=Toggle  a=All  n=None  c=Clean",
            id="clean-header",
        )
        yield Static("Press [bold]s[/bold] to scan for reclaimable space", id="clean-summary")
        yield Static("", id="clean-status")
        yield CleanerTable(id="clean-table")
        yield Static("Details", id="clean-detail-label")
        yield DataTable(id="clean-detail")

    def on_mount(self) -> None:
        detail = self.query_one("#clean-detail", DataTable)
        detail.cursor_type = "row"
        detail.zebra_stripes = True
        detail.add_columns("Path / Name", "Size")
        self.query_one("#clean-detail-label").display = False
        self.query_one("#clean-detail").display = False

    def set_scan_results(self, results: list[ScanResult]) -> None:
        """Called from app after scan completes."""
        self._scan_results = results
        self._scanning = False

        table = self.query_one("#clean-table", CleanerTable)
        table.load_results(results)

        if results:
            total = sum(r.total_bytes for r in results)
            cats = len(results)
            self.query_one("#clean-summary", Static).update(
                f"Reclaimable: [bold]{_fmt_bytes(total)}[/bold] across {cats} categories"
            )
        else:
            self.query_one("#clean-summary", Static).update("No reclaimable space found")
        self.query_one("#clean-status", Static).update("")

    def set_scanning(self) -> None:
        """Show scanning state."""
        self._scanning = True
        self.query_one("#clean-summary", Static).update("Scanning...")
        self.query_one("#clean-status", Static).update("")
        self.query_one("#clean-detail-label").display = False
        self.query_one("#clean-detail").display = False

    def set_cleaning(self) -> None:
        self.query_one("#clean-status", Static).update("Cleaning...")

    def set_clean_done(self, message: str) -> None:
        self.query_one("#clean-status", Static).update(message)

    def show_detail(self) -> None:
        """Show details for the currently highlighted category."""
        table = self.query_one("#clean-table", CleanerTable)
        cat_id = table.get_highlighted_category()
        if cat_id is None:
            return

        result = None
        for r in self._scan_results:
            if r.category_id == cat_id:
                result = r
                break
        if result is None:
            return

        detail = self.query_one("#clean-detail", DataTable)
        detail.clear()
        for item in result.items[:100]:  # Limit for performance
            desc = item.description
            if len(desc) > 70:
                desc = desc[:67] + "..."
            detail.add_row(desc, _fmt_bytes(item.size))

        self.query_one("#clean-detail-label", Static).update(
            f"Details: {result.display_name} ({len(result.items)} items)"
        )
        self.query_one("#clean-detail-label").display = True
        self.query_one("#clean-detail").display = True

    def toggle_select(self) -> None:
        self.query_one("#clean-table", CleanerTable).toggle_selected()
        self._update_summary()

    def select_all(self) -> None:
        self.query_one("#clean-table", CleanerTable).select_all()
        self._update_summary()

    def deselect_all(self) -> None:
        self.query_one("#clean-table", CleanerTable).deselect_all()
        self._update_summary()

    def get_selected_categories(self) -> set[str]:
        return self.query_one("#clean-table", CleanerTable).get_selected_categories()

    def get_selected_total_bytes(self) -> int:
        return self.query_one("#clean-table", CleanerTable).get_selected_total_bytes()

    @property
    def scan_results(self) -> list[ScanResult]:
        return self._scan_results

    @property
    def is_scanning(self) -> bool:
        return self._scanning

    def _update_summary(self) -> None:
        """Update summary line with selected totals."""
        if not self._scan_results:
            return
        table = self.query_one("#clean-table", CleanerTable)
        selected = table.get_selected_categories()
        selected_bytes = table.get_selected_total_bytes()
        total = sum(r.total_bytes for r in self._scan_results)
        cats = len(self._scan_results)

        if selected:
            self.query_one("#clean-summary", Static).update(
                f"Reclaimable: [bold]{_fmt_bytes(total)}[/bold] across {cats} categories "
                f"| Selected: [bold]{_fmt_bytes(selected_bytes)}[/bold] ({len(selected)} categories)"
            )
        else:
            self.query_one("#clean-summary", Static).update(
                f"Reclaimable: [bold]{_fmt_bytes(total)}[/bold] across {cats} categories"
            )
