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
        height: 14;
        margin: 0 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._scan_results: list[ScanResult] = []
        self._scanning = False
        self._detail_category: str | None = None
        self._excluded_items: dict[str, set[str]] = {}

    def compose(self) -> ComposeResult:
        yield Static(
            "Disk Cleaner | s=Scan  Space=Toggle  a=All  n=None  c=Clean  d=Detail",
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
        detail.add_columns("", "Path / Name", "Size")
        self.query_one("#clean-detail-label").display = False
        self.query_one("#clean-detail").display = False

    def set_scan_results(self, results: list[ScanResult]) -> None:
        """Called from app after scan completes."""
        self._scan_results = results
        self._scanning = False
        self._excluded_items.clear()

        table = self.query_one("#clean-table", CleanerTable)
        table.load_results(results)

        # Close detail if open
        self._detail_category = None
        self.query_one("#clean-detail-label").display = False
        self.query_one("#clean-detail").display = False

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
        self._detail_category = None
        self.query_one("#clean-detail-label").display = False
        self.query_one("#clean-detail").display = False

    def set_cleaning(self) -> None:
        self.query_one("#clean-status", Static).update("Cleaning...")

    def set_clean_done(self, message: str) -> None:
        self.query_one("#clean-status", Static).update(message)

    # --- Detail panel ---

    def toggle_detail(self) -> None:
        """Toggle detail panel for the highlighted category."""
        detail_label = self.query_one("#clean-detail-label")
        detail = self.query_one("#clean-detail", DataTable)
        table = self.query_one("#clean-table", CleanerTable)

        cat_id = table.get_highlighted_category()

        # If detail is open for same category -> close
        if self._detail_category == cat_id and detail_label.display:
            self._detail_category = None
            detail_label.display = False
            detail.display = False
            table.focus()
            return

        if cat_id is None:
            return

        result = self._find_result(cat_id)
        if result is None:
            return

        self._detail_category = cat_id
        self._render_detail(result)
        detail_label.display = True
        detail.display = True
        detail.focus()

    def toggle_detail_item(self) -> None:
        """Toggle selection of highlighted item in detail view."""
        if self._detail_category is None:
            return

        detail = self.query_one("#clean-detail", DataTable)
        if detail.row_count == 0:
            return

        try:
            row_key, _ = detail.coordinate_to_cell_key(detail.cursor_coordinate)
            item_path = row_key.value
        except Exception:
            return

        cat_id = self._detail_category
        if cat_id not in self._excluded_items:
            self._excluded_items[cat_id] = set()

        if item_path in self._excluded_items[cat_id]:
            self._excluded_items[cat_id].discard(item_path)
        else:
            self._excluded_items[cat_id].add(item_path)

        cursor_row = detail.cursor_coordinate.row
        result = self._find_result(cat_id)
        if result:
            self._render_detail(result)
            if cursor_row < detail.row_count:
                detail.move_cursor(row=cursor_row)
        self._update_summary()

    def select_all_detail_items(self) -> None:
        """Select all items in the current detail view."""
        if self._detail_category is None:
            return
        self._excluded_items.pop(self._detail_category, None)
        result = self._find_result(self._detail_category)
        if result:
            self._render_detail(result)
        self._update_summary()

    def deselect_all_detail_items(self) -> None:
        """Deselect all items in the current detail view."""
        if self._detail_category is None:
            return
        result = self._find_result(self._detail_category)
        if result:
            self._excluded_items[self._detail_category] = {i.path for i in result.items}
            self._render_detail(result)
        self._update_summary()

    @property
    def is_detail_focused(self) -> bool:
        if self._detail_category is None:
            return False
        return self.query_one("#clean-detail", DataTable).has_focus

    def _find_result(self, cat_id: str) -> ScanResult | None:
        for r in self._scan_results:
            if r.category_id == cat_id:
                return r
        return None

    def _render_detail(self, result: ScanResult) -> None:
        """Render detail table rows with checkboxes."""
        detail = self.query_one("#clean-detail", DataTable)
        excluded = self._excluded_items.get(result.category_id, set())
        detail.clear()
        for item in result.items[:200]:
            check = "[ ]" if item.path in excluded else "[✓]"
            desc = item.description
            if len(desc) > 70:
                desc = desc[:67] + "..."
            detail.add_row(check, desc, _fmt_bytes(item.size), key=item.path)

        n_excluded = len(excluded & {i.path for i in result.items})
        n_total = len(result.items)
        n_selected = n_total - n_excluded
        self.query_one("#clean-detail-label", Static).update(
            f"Details: {result.display_name} ({n_selected}/{n_total} selected) "
            f"| [bold]Space[/bold]=Toggle  [bold]d[/bold]=Close"
        )

    # --- Category selection ---

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

    def get_effective_scan_results(self) -> list[ScanResult]:
        """Return scan results with excluded items filtered out."""
        if not self._excluded_items:
            return self._scan_results

        effective: list[ScanResult] = []
        for r in self._scan_results:
            excluded = self._excluded_items.get(r.category_id, set())
            if not excluded:
                effective.append(r)
                continue
            items = [i for i in r.items if i.path not in excluded]
            if items:
                total = sum(i.size for i in items)
                effective.append(ScanResult(
                    category_id=r.category_id,
                    display_name=r.display_name,
                    total_bytes=total,
                    items=items,
                    needs_root=r.needs_root,
                    item_label=r.item_label,
                ))
        return effective

    def get_selected_total_bytes(self) -> int:
        """Total bytes for selected categories, respecting item exclusions."""
        selected = self.get_selected_categories()
        effective = self.get_effective_scan_results()
        return sum(r.total_bytes for r in effective if r.category_id in selected)

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
        selected_bytes = self.get_selected_total_bytes()
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
