"""Process table widget."""

from __future__ import annotations

from typing import Any

from textual.widgets import DataTable


def _fmt_bytes(b: int) -> str:
    if b >= 1_073_741_824:
        return f"{b / 1_073_741_824:.1f}G"
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f}M"
    if b >= 1024:
        return f"{b / 1024:.0f}K"
    return f"{b}B"


_STATE_MAP = {
    "R": "Running",
    "S": "Sleeping",
    "D": "Disk",
    "T": "Stopped",
    "Z": "Zombie",
    "I": "Idle",
    "t": "Traced",
}


class ProcessTable(DataTable):
    DEFAULT_CSS = """
    ProcessTable {
        height: 1fr;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._filter_text: str = ""
        self._sort_col: str = "cpu"
        self._sort_reverse: bool = True

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_columns("PID", "Name", "CPU%", "RSS", "State", "Command")

    def load_processes(self, processes: list[dict[str, Any]]) -> None:
        # Apply filter
        if self._filter_text:
            ft = self._filter_text.lower()
            processes = [p for p in processes if ft in p.get("name", "").lower()
                        or ft in p.get("cmdline", "").lower()
                        or ft in str(p.get("pid", ""))]

        self.clear()
        for proc in processes[:200]:  # Limit for performance
            pid = proc.get("pid", 0)
            name = proc.get("name", "")
            cpu = proc.get("cpu_percent", 0.0)
            rss = proc.get("rss", 0)
            state = _STATE_MAP.get(proc.get("state", "?"), proc.get("state", "?"))
            cmdline = proc.get("cmdline", "")
            if len(cmdline) > 80:
                cmdline = cmdline[:77] + "..."

            self.add_row(
                str(pid), name, f"{cpu:.1f}", _fmt_bytes(rss), state, cmdline,
                key=str(pid),
            )

    def set_filter(self, text: str) -> None:
        self._filter_text = text

    def get_selected_pid(self) -> int | None:
        if self.row_count == 0:
            return None
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            return int(row_key.value)
        except (ValueError, Exception):
            return None
