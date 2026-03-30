"""CPU detail tab — per-core frequencies, temps, governor."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, DataTable

from sysward.widgets.line_chart import LineChart
from sysward.widgets.usage_bar import UsageBar


class CPUDetailScreen(Vertical):
    """Detailed CPU tab content."""

    DEFAULT_CSS = """
    CPUDetailScreen {
        height: 1fr;
        padding: 1;
    }
    CPUDetailScreen #cpu-summary {
        height: 3;
        padding: 0 1;
    }
    CPUDetailScreen #cpu-chart {
        height: 12;
        margin: 0 1;
    }
    CPUDetailScreen #core-table {
        margin: 1;
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="cpu-summary")
        yield LineChart("CPU Usage", y_label="%", y_range=(0, 100), id="cpu-chart")
        yield DataTable(id="core-table")

    def on_mount(self) -> None:
        table = self.query_one("#core-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("Core", "Usage%", "Freq MHz", "Governor")

    def update_metrics(self, metrics: dict[str, Any], history: dict) -> None:
        cpu = metrics.get("cpu", {})
        sensors = metrics.get("sensors", {})

        # Summary
        usage = cpu.get("usage", 0)
        freq_avg = cpu.get("freq_avg", 0)
        freq_max_cap = cpu.get("freq_max_capable", 0)
        gov = cpu.get("governor", "?")
        epp = cpu.get("epp", "?")
        turbo = cpu.get("turbo")
        turbo_str = "on" if turbo else ("off" if turbo is not None else "?")
        pkg_temp = sensors.get("package_temp", 0)
        fan = sensors.get("fan_rpm", 0)

        summary = (
            f"Total: {usage:.1f}% | Avg Freq: {freq_avg:.0f}/{freq_max_cap:.0f} MHz | "
            f"Governor: {gov} | EPP: {epp} | Turbo: {turbo_str}\n"
            f"Package: {pkg_temp:.0f}°C | Fan: {fan} RPM | "
            f"Cores: {cpu.get('core_count', 0)}"
        )
        try:
            self.query_one("#cpu-summary", Static).update(summary)
        except Exception:
            pass

        # Chart
        cpu_hist = history.get("cpu_usage")
        if cpu_hist:
            try:
                self.query_one("#cpu-chart", LineChart).update_from_ring(
                    cpu_hist.last_n_with_time(300), color="cyan"
                )
            except Exception:
                pass

        # Per-core table
        per_core = cpu.get("per_core_usage", [])
        freqs = cpu.get("frequencies", [])
        governors = cpu.get("governors", [])
        cpu_temps = sensors.get("cpu_temps", {})

        table = self.query_one("#core-table", DataTable)
        table.clear()
        for i, usage_pct in enumerate(per_core):
            freq = freqs[i] if i < len(freqs) else 0
            gov = governors[i] if i < len(governors) else "?"
            table.add_row(
                f"Core {i}", f"{usage_pct:.1f}", f"{freq:.0f}", gov,
                key=f"core-{i}",
            )
