"""Memory detail tab — RAM/Swap breakdown."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from sysward.widgets.line_chart import LineChart
from sysward.widgets.usage_bar import UsageBar


def _fmt(b: int | float) -> str:
    if b >= 1_073_741_824:
        return f"{b / 1_073_741_824:.1f} GiB"
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MiB"
    return f"{b / 1024:.0f} KiB"


class MemoryDetailScreen(Vertical):
    """Detailed memory tab content."""

    DEFAULT_CSS = """
    MemoryDetailScreen {
        height: 1fr;
        padding: 1;
    }
    MemoryDetailScreen .mem-section {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }
    MemoryDetailScreen #ram-chart {
        height: 12;
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", classes="mem-section", id="ram-info")
        yield UsageBar("RAM", id="ram-bar")
        yield LineChart("RAM Usage", y_label="%", y_range=(0, 100), id="ram-chart")
        yield Static("", classes="mem-section", id="swap-info")
        yield UsageBar("Swap", id="swap-bar")
        yield Static("", classes="mem-section", id="zram-info")

    def update_metrics(self, metrics: dict[str, Any], history: dict) -> None:
        mem = metrics.get("memory", {})

        # RAM
        total = mem.get("total", 0)
        used = mem.get("used", 0)
        available = mem.get("available", 0)
        cached = mem.get("cached", 0)
        buffers = mem.get("buffers", 0)
        pct = mem.get("usage_percent", 0)

        ram_info = (
            f"Total: {_fmt(total)} | Used: {_fmt(used)} | Available: {_fmt(available)}\n"
            f"Cached: {_fmt(cached)} | Buffers: {_fmt(buffers)}"
        )
        try:
            self.query_one("#ram-info", Static).update(ram_info)
            self.query_one("#ram-bar", UsageBar).value = pct
        except Exception:
            pass

        # Chart
        ram_hist = history.get("ram_usage")
        if ram_hist:
            try:
                self.query_one("#ram-chart", LineChart).update_from_ring(
                    ram_hist.last_n_with_time(300), color="green"
                )
            except Exception:
                pass

        # Swap
        swap_total = mem.get("swap_total", 0)
        swap_used = mem.get("swap_used", 0)
        swap_pct = mem.get("swap_percent", 0)

        swap_info = f"Swap Total: {_fmt(swap_total)} | Used: {_fmt(swap_used)}"
        try:
            self.query_one("#swap-info", Static).update(swap_info)
            self.query_one("#swap-bar", UsageBar).value = swap_pct
        except Exception:
            pass

        # zram
        zram_devs = mem.get("zram_devices", [])
        if zram_devs:
            parts = []
            for z in zram_devs:
                name = z["name"]
                ds = _fmt(z["disksize"])
                orig = _fmt(z["orig_size"])
                compr = _fmt(z["compr_size"])
                ratio = (z["orig_size"] / z["compr_size"]) if z["compr_size"] > 0 else 0
                parts.append(f"{name}: {ds} disk, {orig} orig, {compr} compr ({ratio:.1f}x)")
            try:
                self.query_one("#zram-info", Static).update("\n".join(parts))
            except Exception:
                pass
