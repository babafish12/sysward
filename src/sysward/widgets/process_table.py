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

# Column keys used for in-place cell updates.
_COL_KEYS = ("pid", "name", "cpu", "rss", "state", "cmd")


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
        # Track the ordered list of row keys (PIDs as strings) currently in the table.
        self._current_row_keys: list[str] = []

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_column("PID", key="pid")
        self.add_column("Name", key="name")
        self.add_column("CPU%", key="cpu")
        self.add_column("RSS", key="rss")
        self.add_column("State", key="state")
        self.add_column("Command", key="cmd")

    @staticmethod
    def _proc_to_cells(proc: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
        """Convert a process dict to the 6-cell tuple displayed in a row."""
        pid = str(proc.get("pid", 0))
        name = proc.get("name", "")
        cpu = f"{proc.get('cpu_percent', 0.0):.1f}"
        rss = _fmt_bytes(proc.get("rss", 0))
        state = _STATE_MAP.get(proc.get("state", "?"), proc.get("state", "?"))
        cmdline = proc.get("cmdline", "")
        if len(cmdline) > 80:
            cmdline = cmdline[:77] + "..."
        return pid, name, cpu, rss, state, cmdline

    def load_processes(self, processes: list[dict[str, Any]]) -> None:
        """Update the process table in-place to preserve scroll position.

        Instead of clear() + add_row() (which resets scroll/cursor), this
        method diffs the current rows against the new data and uses
        update_cell() for existing rows, add_row() for new PIDs, and
        remove_row() for PIDs that disappeared.
        """
        # Apply filter
        if self._filter_text:
            ft = self._filter_text.lower()
            processes = [
                p for p in processes
                if ft in p.get("name", "").lower()
                or ft in p.get("cmdline", "").lower()
                or ft in str(p.get("pid", ""))
            ]

        # Build the desired row list (max 200 entries).
        desired: list[tuple[str, tuple[str, str, str, str, str, str]]] = []
        for proc in processes[:200]:
            key = str(proc.get("pid", 0))
            cells = self._proc_to_cells(proc)
            desired.append((key, cells))

        desired_keys = [k for k, _ in desired]
        desired_map = {k: cells for k, cells in desired}

        # If the table is empty (first load), just add everything.
        if not self._current_row_keys:
            for key, cells in desired:
                self.add_row(*cells, key=key)
            self._current_row_keys = desired_keys
            return

        old_keys_set = set(self._current_row_keys)
        new_keys_set = set(desired_keys)

        # --- 1. Remove rows that are no longer present ---
        removed = old_keys_set - new_keys_set
        for key in removed:
            try:
                self.remove_row(key)
            except Exception:
                pass
        # Update our tracking list after removals.
        if removed:
            self._current_row_keys = [
                k for k in self._current_row_keys if k not in removed
            ]

        # --- 2. Update cells of existing rows ---
        for key in self._current_row_keys:
            if key in desired_map:
                new_cells = desired_map[key]
                try:
                    old_cells = self.get_row(key)
                except Exception:
                    continue
                for i, col_key in enumerate(_COL_KEYS):
                    if i < len(old_cells) and str(old_cells[i]) != str(new_cells[i]):
                        self.update_cell(key, col_key, new_cells[i])

        # --- 3. Add rows that are new ---
        added = new_keys_set - old_keys_set
        if added:
            for key in desired_keys:
                if key in added:
                    cells = desired_map[key]
                    self.add_row(*cells, key=key)

        # --- 4. Reorder if the sort order changed ---
        # DataTable does not natively support reordering, so if the order
        # changed significantly we need to rebuild.  We check whether the
        # key order matches; if not, we do a full rebuild but save/restore
        # the scroll offset (not just cursor) to keep the view stable.
        current_after_update = (
            self._current_row_keys
            + [k for k in desired_keys if k in added]
        )

        if current_after_update != desired_keys:
            # Order differs — must rebuild, but preserve scroll offset.
            saved_scroll_y = self.scroll_y
            saved_key: str | None = None
            if self.row_count > 0:
                try:
                    row_key, _ = self.coordinate_to_cell_key(
                        self.cursor_coordinate
                    )
                    saved_key = row_key.value
                except Exception:
                    pass

            self.clear()
            restore_row = 0
            for idx, (key, cells) in enumerate(desired):
                self.add_row(*cells, key=key)
                if key == saved_key:
                    restore_row = idx

            self._current_row_keys = desired_keys

            # Restore cursor and scroll position after DOM settles.
            if self.row_count > 0:
                restore_row = min(restore_row, self.row_count - 1)
                self.move_cursor(row=restore_row)

                def _restore_scroll() -> None:
                    self.scroll_y = saved_scroll_y

                self.call_later(_restore_scroll)
        else:
            self._current_row_keys = desired_keys

    def set_filter(self, text: str) -> None:
        self._filter_text = text
        # Reset tracking so next load_processes does a full rebuild,
        # which is fine when the user is actively typing a filter.
        self._current_row_keys = []

    def get_selected_pid(self) -> int | None:
        if self.row_count == 0:
            return None
        try:
            row_key, _ = self.coordinate_to_cell_key(self.cursor_coordinate)
            return int(row_key.value)
        except (ValueError, Exception):
            return None
