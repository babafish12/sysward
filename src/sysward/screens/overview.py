"""Overview screen -- btop-inspired dashboard."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Sparkline

from sysward.widgets.gauge import Gauge


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
    """btop-inspired overview dashboard."""

    DEFAULT_CSS = """
    OverviewScreen {
        height: 1fr;
        padding: 1;
    }

    /* Top row: CPU + RAM panels side by side */
    OverviewScreen #top-row {
        height: auto;
        min-height: 7;
    }
    OverviewScreen .metric-panel {
        width: 1fr;
        height: auto;
        min-height: 6;
        border: round $panel;
        background: $surface;
        padding: 0 1;
        margin: 0 1 1 0;
    }
    OverviewScreen .panel-title {
        color: $primary;
        text-style: bold;
        height: 1;
    }
    OverviewScreen .panel-detail {
        height: 1;
        color: $foreground;
    }
    OverviewScreen Sparkline {
        height: 2;
    }

    /* Middle row: GPU + Battery + Temps */
    OverviewScreen #mid-row {
        height: auto;
        min-height: 4;
        margin-bottom: 1;
    }
    OverviewScreen .mid-panel {
        width: 1fr;
        height: auto;
        border: round $panel;
        background: $surface;
        padding: 0 1;
        margin: 0 1 0 0;
    }

    /* Bottom row: Net + Disk + Fan */
    OverviewScreen #bot-row {
        height: auto;
        min-height: 3;
    }
    OverviewScreen .bot-panel {
        width: 1fr;
        height: auto;
        border: round $panel;
        background: $surface;
        padding: 0 1;
        margin: 0 1 0 0;
    }
    """

    def compose(self) -> ComposeResult:
        # Top: CPU + RAM with gauges and sparklines
        with Horizontal(id="top-row"):
            with Vertical(classes="metric-panel"):
                yield Static("CPU", classes="panel-title")
                yield Gauge("Usage", id="cpu-gauge")
                yield Static("", id="cpu-detail", classes="panel-detail")
                yield Sparkline([], id="cpu-spark")
            with Vertical(classes="metric-panel"):
                yield Static("Memory", classes="panel-title")
                yield Gauge("RAM", id="ram-gauge")
                yield Static("", id="ram-detail", classes="panel-detail")
                yield Sparkline([], id="ram-spark")

        # Middle: GPU + Battery + Temps
        with Horizontal(id="mid-row"):
            with Vertical(classes="mid-panel"):
                yield Static("GPU", classes="panel-title")
                yield Gauge("Freq", id="gpu-gauge")
                yield Static("", id="gpu-detail", classes="panel-detail")
            with Vertical(classes="mid-panel"):
                yield Static("Battery", classes="panel-title")
                yield Gauge("Charge", id="bat-gauge", warn_threshold=30, crit_threshold=15)
                yield Static("", id="bat-detail", classes="panel-detail")
            with Vertical(classes="mid-panel"):
                yield Static("Temperatures", classes="panel-title")
                yield Static("", id="temp-info")

        # Bottom: Network + Disk + Fan
        with Horizontal(id="bot-row"):
            with Vertical(classes="bot-panel"):
                yield Static("Network", classes="panel-title")
                yield Static("", id="net-info")
            with Vertical(classes="bot-panel"):
                yield Static("Disk I/O", classes="panel-title")
                yield Static("", id="disk-info")
            with Vertical(classes="bot-panel"):
                yield Static("Fans", classes="panel-title")
                yield Static("", id="fan-info")

    def update_metrics(self, metrics: dict[str, Any], history: dict) -> None:
        # CPU
        cpu = metrics.get("cpu", {})
        cpu_usage = cpu.get("usage", 0)
        freq = cpu.get("freq_avg", 0)
        gov = cpu.get("governor", "?")
        cores = cpu.get("core_count", 0)
        try:
            self.query_one("#cpu-gauge", Gauge).value = cpu_usage
            self.query_one("#cpu-detail", Static).update(
                f"{cores}C | {freq:.0f} MHz | {gov}"
            )
        except Exception:
            pass
        cpu_hist = history.get("cpu_usage")
        if cpu_hist:
            try:
                self.query_one("#cpu-spark", Sparkline).data = cpu_hist.last_n(60)
            except Exception:
                pass

        # RAM
        mem = metrics.get("memory", {})
        ram_pct = mem.get("usage_percent", 0)
        ram_used = mem.get("used", 0)
        ram_total = mem.get("total", 0)
        try:
            self.query_one("#ram-gauge", Gauge).value = ram_pct
            self.query_one("#ram-detail", Static).update(
                f"{_fmt_bytes(ram_used)} / {_fmt_bytes(ram_total)}"
            )
        except Exception:
            pass
        ram_hist = history.get("ram_usage")
        if ram_hist:
            try:
                self.query_one("#ram-spark", Sparkline).data = ram_hist.last_n(60)
            except Exception:
                pass

        # GPU
        gpu = metrics.get("gpu", {})
        gpu_freq = gpu.get("freq_cur", 0)
        gpu_max = gpu.get("freq_max", 1)
        gpu_pct = (gpu_freq / gpu_max * 100) if gpu_max > 0 else 0
        try:
            self.query_one("#gpu-gauge", Gauge).value = gpu_pct
            self.query_one("#gpu-detail", Static).update(f"{gpu_freq} / {gpu_max} MHz")
        except Exception:
            pass

        # Battery
        bat = metrics.get("battery", {})
        bat_cap = bat.get("capacity", 0)
        bat_status = bat.get("status", "Unknown")
        power = bat.get("power_draw", 0)
        try:
            self.query_one("#bat-gauge", Gauge).value = float(bat_cap)
            detail = bat_status
            if power:
                detail += f" | {power:.1f}W"
            self.query_one("#bat-detail", Static).update(detail)
        except Exception:
            pass

        # Temperatures
        sensors = metrics.get("sensors", {})
        pkg_temp = sensors.get("package_temp", 0)
        cpu_temps = sensors.get("cpu_temps", {})
        nvme_temps = sensors.get("nvme_temps", {})
        wifi_temps = sensors.get("wifi_temps", {})
        temp_parts = []
        if pkg_temp:
            color = "red" if pkg_temp >= 80 else "yellow" if pkg_temp >= 60 else "green"
            temp_parts.append(f"CPU: {pkg_temp:.0f}\u00b0C")
        for label, val in list(nvme_temps.items())[:2]:
            temp_parts.append(f"NVMe: {val:.0f}\u00b0C")
        for label, val in list(wifi_temps.items())[:1]:
            temp_parts.append(f"WiFi: {val:.0f}\u00b0C")
        try:
            self.query_one("#temp-info", Static).update("  ".join(temp_parts) if temp_parts else "No sensors")
        except Exception:
            pass

        # Network
        net = metrics.get("network", {})
        ifaces = net.get("interfaces", [])
        net_parts = []
        for iface in ifaces:
            if iface.get("state") == "up" or iface.get("rx_rate", 0) > 0:
                name = iface["name"]
                rx = _fmt_rate(iface.get("rx_rate", 0))
                tx = _fmt_rate(iface.get("tx_rate", 0))
                net_parts.append(f"{name} \u2193{rx} \u2191{tx}")
        try:
            self.query_one("#net-info", Static).update("\n".join(net_parts) if net_parts else "No active interfaces")
        except Exception:
            pass

        # Disk I/O
        disk = metrics.get("disk", {})
        devs = disk.get("devices", [])
        disk_parts = []
        for dev in devs:
            r = _fmt_rate(dev.get("read_bytes_s", 0))
            w = _fmt_rate(dev.get("write_bytes_s", 0))
            disk_parts.append(f"{dev['name']} R:{r} W:{w}")
        try:
            self.query_one("#disk-info", Static).update("\n".join(disk_parts) if disk_parts else "No disk I/O")
        except Exception:
            pass

        # Fan info
        fan_rpm = sensors.get("fan_rpm", 0)
        try:
            fan_str = f"{fan_rpm} RPM" if fan_rpm else "No fan data"
            self.query_one("#fan-info", Static).update(fan_str)
        except Exception:
            pass
