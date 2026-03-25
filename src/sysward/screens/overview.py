"""Overview screen — main dashboard with summary metric cards."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.widgets import Static

from sysward.widgets.metric_card import MetricCard
from sysward.widgets.usage_bar import UsageBar


def _fmt_bytes(b: int | float) -> str:
    if b >= 1_073_741_824:
        return f"{b / 1_073_741_824:.1f}G"
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f}M"
    if b >= 1024:
        return f"{b / 1024:.0f}K"
    return f"{b:.0f}B"


def _fmt_rate(b: float) -> str:
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MB/s"
    if b >= 1024:
        return f"{b / 1024:.1f} KB/s"
    return f"{b:.0f} B/s"


class OverviewScreen(Vertical):
    """Main overview tab content."""

    DEFAULT_CSS = """
    OverviewScreen {
        height: 1fr;
        padding: 1;
    }
    OverviewScreen #cards-row {
        height: auto;
        min-height: 8;
    }
    OverviewScreen #extra-info {
        height: auto;
        margin-top: 1;
        padding: 0 1;
    }
    OverviewScreen .info-line {
        height: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Grid(id="cards-row"):
            yield MetricCard("CPU", id="cpu-card")
            yield MetricCard("RAM", id="ram-card")
            yield MetricCard("GPU", id="gpu-card")
            yield MetricCard("Battery", id="bat-card")
        with Vertical(id="extra-info"):
            yield Static("", classes="info-line", id="sensor-info")
            yield Static("", classes="info-line", id="net-info")
            yield Static("", classes="info-line", id="disk-info")

    def on_mount(self) -> None:
        # Style the grid
        grid = self.query_one("#cards-row", Grid)
        grid.styles.grid_size_columns = 2
        grid.styles.grid_size_rows = 2
        grid.styles.grid_gutter_horizontal = 1
        grid.styles.grid_gutter_vertical = 1

    def update_metrics(self, metrics: dict[str, Any], history: dict) -> None:
        """Update all cards with latest metrics."""
        # CPU
        cpu = metrics.get("cpu", {})
        cpu_card = self.query_one("#cpu-card", MetricCard)
        cpu_usage = cpu.get("usage", 0)
        freq = cpu.get("freq_avg", 0)
        gov = cpu.get("governor", "?")
        cpu_card.value = cpu_usage
        cpu_card.detail_text = f"{freq:.0f} MHz | {gov}"
        cpu_hist = history.get("cpu_usage")
        if cpu_hist:
            cpu_card.update_sparkline(cpu_hist.last_n(60))

        # RAM
        mem = metrics.get("memory", {})
        ram_card = self.query_one("#ram-card", MetricCard)
        ram_pct = mem.get("usage_percent", 0)
        ram_used = mem.get("used", 0)
        ram_total = mem.get("total", 0)
        ram_card.value = ram_pct
        ram_card.detail_text = f"{_fmt_bytes(ram_used)} / {_fmt_bytes(ram_total)}"
        ram_hist = history.get("ram_usage")
        if ram_hist:
            ram_card.update_sparkline(ram_hist.last_n(60))

        # GPU
        gpu = metrics.get("gpu", {})
        gpu_card = self.query_one("#gpu-card", MetricCard)
        gpu_freq = gpu.get("freq_cur", 0)
        gpu_max = gpu.get("freq_max", 1)
        gpu_pct = (gpu_freq / gpu_max * 100) if gpu_max > 0 else 0
        gpu_card.value = gpu_pct
        gpu_card.detail_text = f"{gpu_freq} / {gpu_max} MHz"
        gpu_hist = history.get("gpu_freq")
        if gpu_hist:
            gpu_card.update_sparkline(gpu_hist.last_n(60))

        # Battery
        bat = metrics.get("battery", {})
        bat_card = self.query_one("#bat-card", MetricCard)
        bat_cap = bat.get("capacity", 0)
        bat_status = bat.get("status", "Unknown")
        power = bat.get("power_draw", 0)
        bat_card.value = float(bat_cap)
        detail = bat_status
        if power:
            detail += f" | {power:.1f}W"
        bat_card.detail_text = detail

        # Sensor info line
        sensors = metrics.get("sensors", {})
        pkg_temp = sensors.get("package_temp", 0)
        fan_rpm = sensors.get("fan_rpm", 0)
        sensor_str = ""
        if pkg_temp:
            sensor_str += f"Package: {pkg_temp:.0f}°C"
        if fan_rpm:
            sensor_str += f"  Fan: {fan_rpm} RPM"
        try:
            self.query_one("#sensor-info", Static).update(sensor_str)
        except Exception:
            pass

        # Network info line
        net = metrics.get("network", {})
        ifaces = net.get("interfaces", [])
        net_parts = []
        for iface in ifaces:
            if iface.get("state") == "up" or iface.get("rx_rate", 0) > 0:
                name = iface["name"]
                rx = _fmt_rate(iface.get("rx_rate", 0))
                tx = _fmt_rate(iface.get("tx_rate", 0))
                net_parts.append(f"{name} ↓{rx} ↑{tx}")
        try:
            self.query_one("#net-info", Static).update("  ".join(net_parts) if net_parts else "")
        except Exception:
            pass

        # Disk info line
        disk = metrics.get("disk", {})
        devs = disk.get("devices", [])
        disk_parts = []
        for dev in devs:
            r = _fmt_rate(dev.get("read_bytes_s", 0))
            w = _fmt_rate(dev.get("write_bytes_s", 0))
            disk_parts.append(f"{dev['name']} R {r}  W {w}")
        try:
            self.query_one("#disk-info", Static).update("  ".join(disk_parts) if disk_parts else "")
        except Exception:
            pass
