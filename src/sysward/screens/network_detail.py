"""Network detail tab — per-interface throughput."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, DataTable

from sysward.widgets.line_chart import LineChart


def _fmt_bytes(b: int | float) -> str:
    if b >= 1_073_741_824:
        return f"{b / 1_073_741_824:.1f} GiB"
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MiB"
    if b >= 1024:
        return f"{b / 1024:.0f} KiB"
    return f"{b:.0f} B"


def _fmt_rate(b: float) -> str:
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MB/s"
    if b >= 1024:
        return f"{b / 1024:.1f} KB/s"
    return f"{b:.0f} B/s"


class NetworkDetailScreen(Vertical):
    """Detailed network tab content."""

    DEFAULT_CSS = """
    NetworkDetailScreen {
        height: 1fr;
        padding: 1;
    }
    NetworkDetailScreen #net-chart {
        height: 12;
        margin: 0 1 1 1;
    }
    NetworkDetailScreen #iface-table {
        height: 1fr;
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield LineChart("Network Throughput", y_label="B/s", id="net-chart")
        yield DataTable(id="iface-table")

    def on_mount(self) -> None:
        table = self.query_one("#iface-table", DataTable)
        table.zebra_stripes = True
        table.add_columns("Interface", "State", "RX Rate", "TX Rate", "Total RX", "Total TX")

    def update_metrics(self, metrics: dict[str, Any], history: dict) -> None:
        net = metrics.get("network", {})
        ifaces = net.get("interfaces", [])

        # Chart
        rx_hist = history.get("net_rx")
        tx_hist = history.get("net_tx")
        try:
            chart = self.query_one("#net-chart", LineChart)
            if rx_hist:
                chart.update_from_ring(rx_hist.last_n_with_time(300), series_name="RX", color="green")
            if tx_hist:
                chart.update_from_ring(tx_hist.last_n_with_time(300), series_name="TX", color="red")
        except Exception:
            pass

        # Table
        table = self.query_one("#iface-table", DataTable)
        table.clear()
        for iface in ifaces:
            table.add_row(
                iface["name"],
                iface.get("state", "?"),
                _fmt_rate(iface.get("rx_rate", 0)),
                _fmt_rate(iface.get("tx_rate", 0)),
                _fmt_bytes(iface.get("rx_bytes", 0)),
                _fmt_bytes(iface.get("tx_bytes", 0)),
            )
