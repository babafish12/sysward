"""Systemd service table widget."""

from __future__ import annotations

from typing import Any

from textual.widgets import DataTable


class ServiceTable(DataTable):
    DEFAULT_CSS = """
    ServiceTable {
        height: 1fr;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._filter_text: str = ""

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_columns("Unit", "Active", "Sub", "Description")

    def load_services(self, services: list[dict[str, str]]) -> None:
        if self._filter_text:
            ft = self._filter_text.lower()
            services = [s for s in services if ft in s.get("unit", "").lower()
                       or ft in s.get("description", "").lower()]

        self.clear()
        for svc in services:
            unit = svc.get("unit", "")
            active = svc.get("active", "")
            sub = svc.get("sub", "")
            desc = svc.get("description", "")
            if len(desc) > 60:
                desc = desc[:57] + "..."

            self.add_row(unit, active, sub, desc, key=unit)

    def set_filter(self, text: str) -> None:
        self._filter_text = text

    def get_selected_unit(self) -> str | None:
        if self.row_count == 0:
            return None
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            return row_key.value
        except Exception:
            return None
