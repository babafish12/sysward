"""Cleaner category table widget."""

from __future__ import annotations

from typing import Any

from textual.widgets import DataTable

from sysward.models.clean_item import ScanResult


def _fmt_bytes(b: int) -> str:
    if b >= 1_073_741_824:
        return f"{b / 1_073_741_824:.1f} GiB"
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MiB"
    if b >= 1024:
        return f"{b / 1024:.0f} KiB"
    return f"{b} B"


class CleanerTable(DataTable):
    """DataTable showing scan categories with selection checkboxes."""

    DEFAULT_CSS = """
    CleanerTable {
        height: 1fr;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._selected: set[str] = set()
        self._results: list[ScanResult] = []

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_columns("", "Category", "Size", "Items", "Note")

    def load_results(self, results: list[ScanResult]) -> None:
        """Load scan results into the table."""
        self._results = results
        self._selected.clear()
        self.clear()
        for result in results:
            check = "[✓]" if result.category_id in self._selected else "[ ]"
            note = "(root)" if result.needs_root else ""
            self.add_row(
                check,
                result.display_name,
                _fmt_bytes(result.total_bytes),
                result.item_label,
                note,
                key=result.category_id,
            )

    def toggle_selected(self, category_id: str | None = None) -> None:
        """Toggle selection of a category. If None, use cursor position."""
        if category_id is None:
            category_id = self.get_highlighted_category()
        if category_id is None:
            return

        if category_id in self._selected:
            self._selected.discard(category_id)
        else:
            self._selected.add(category_id)
        self._refresh_rows()

    def select_all(self) -> None:
        self._selected = {r.category_id for r in self._results}
        self._refresh_rows()

    def deselect_all(self) -> None:
        self._selected.clear()
        self._refresh_rows()

    def get_selected_categories(self) -> set[str]:
        return set(self._selected)

    def get_highlighted_category(self) -> str | None:
        if self.row_count == 0:
            return None
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            return row_key.value
        except Exception:
            return None

    def get_selected_total_bytes(self) -> int:
        return sum(r.total_bytes for r in self._results if r.category_id in self._selected)

    def _refresh_rows(self) -> None:
        """Re-render all rows to update checkboxes."""
        self.clear()
        for result in self._results:
            check = "[✓]" if result.category_id in self._selected else "[ ]"
            note = "(root)" if result.needs_root else ""
            self.add_row(
                check,
                result.display_name,
                _fmt_bytes(result.total_bytes),
                result.item_label,
                note,
                key=result.category_id,
            )
