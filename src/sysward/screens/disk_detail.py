"""Disk detail tab — per-disk I/O and filesystem usage."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, DataTable

from sysward.widgets.usage_bar import UsageBar


def _fmt(b: int | float) -> str:
    if b >= 1_099_511_627_776:
        return f"{b / 1_099_511_627_776:.1f} TiB"
    if b >= 1_073_741_824:
        return f"{b / 1_073_741_824:.1f} GiB"
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MiB"
    return f"{b / 1024:.0f} KiB"


def _fmt_rate(b: float) -> str:
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MB/s"
    if b >= 1024:
        return f"{b / 1024:.1f} KB/s"
    return f"{b:.0f} B/s"


class DiskDetailScreen(Vertical):
    """Detailed disk tab content."""

    DEFAULT_CSS = """
    DiskDetailScreen {
        height: 1fr;
        padding: 1;
    }
    DiskDetailScreen #fs-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    DiskDetailScreen #fs-table {
        height: auto;
        max-height: 10;
        margin-bottom: 1;
    }
    DiskDetailScreen #io-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    DiskDetailScreen #io-table {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Filesystems", id="fs-title")
        yield DataTable(id="fs-table")
        yield Static("Disk I/O", id="io-title")
        yield DataTable(id="io-table")

    def on_mount(self) -> None:
        fs_table = self.query_one("#fs-table", DataTable)
        fs_table.zebra_stripes = True
        fs_table.add_columns("Device", "Mount", "Type", "Total", "Used", "Avail", "Use%")

        io_table = self.query_one("#io-table", DataTable)
        io_table.zebra_stripes = True
        io_table.add_columns("Device", "Read", "Write")

    def update_metrics(self, metrics: dict[str, Any], history: dict) -> None:
        disk = metrics.get("disk", {})

        # Filesystems
        fs_table = self.query_one("#fs-table", DataTable)
        fs_table.clear()
        for fs in disk.get("filesystems", []):
            fs_table.add_row(
                fs["device"], fs["mount"], fs["fstype"],
                _fmt(fs["total"]), _fmt(fs["used"]), _fmt(fs["avail"]),
                f"{fs['percent']:.1f}%",
            )

        # I/O
        io_table = self.query_one("#io-table", DataTable)
        io_table.clear()
        for dev in disk.get("devices", []):
            io_table.add_row(
                dev["name"],
                _fmt_rate(dev["read_bytes_s"]),
                _fmt_rate(dev["write_bytes_s"]),
            )
