"""Fan speed tab — RPM monitoring + ThinkPad fan control."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, DataTable

from sysward.widgets.line_chart import LineChart


class FanScreen(Vertical):
    """Fan speed monitoring and optional ThinkPad control."""

    DEFAULT_CSS = """
    FanScreen {
        height: 1fr;
        padding: 1;
    }
    FanScreen #fan-summary {
        height: 3;
        padding: 0 1;
    }
    FanScreen #fan-chart {
        height: 12;
        margin: 0 1;
    }
    FanScreen #fan-table {
        height: auto;
        max-height: 8;
        margin: 1;
    }
    FanScreen #tp-control {
        height: auto;
        padding: 1;
        margin: 0 1;
        border: round $panel;
        background: $surface;
    }
    FanScreen .tp-title {
        color: $primary;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="fan-summary")
        yield LineChart("Fan RPM History", y_label="RPM", id="fan-chart")
        yield DataTable(id="fan-table")
        with Vertical(id="tp-control"):
            yield Static("ThinkPad Fan Control", classes="tp-title")
            yield Static("", id="tp-status")

    def on_mount(self) -> None:
        table = self.query_one("#fan-table", DataTable)
        table.zebra_stripes = True
        table.add_columns("Fan", "RPM", "Status")

    def update_metrics(self, metrics: dict[str, Any], history: dict) -> None:
        fan_data = metrics.get("fan", {})
        fans = fan_data.get("fans", {})
        tp = fan_data.get("thinkpad")

        # Summary
        if fans:
            rpm_vals = [v for v in fans.values() if v > 0]
            summary = f"Active fans: {len(rpm_vals)}/{len(fans)}"
            if rpm_vals:
                summary += f" | Max RPM: {max(rpm_vals)}"
        else:
            summary = "No fans detected"
        try:
            self.query_one("#fan-summary", Static).update(summary)
        except Exception:
            pass

        # RPM History chart
        fan_hist = history.get("fan_rpm")
        if fan_hist:
            try:
                self.query_one("#fan-chart", LineChart).update_from_ring(
                    fan_hist.last_n_with_time(300), color="cyan"
                )
            except Exception:
                pass

        # Fan table
        try:
            table = self.query_one("#fan-table", DataTable)
            table.clear()
            for label, rpm in sorted(fans.items()):
                status = "Active" if rpm > 0 else "Stopped"
                table.add_row(label, str(rpm), status)
        except Exception:
            pass

        # ThinkPad control panel
        try:
            tp_control = self.query_one("#tp-control", Vertical)
            if tp is None or not tp.get("available"):
                tp_control.display = False
            else:
                tp_control.display = True
                level = tp.get("level", "?")
                speed = tp.get("speed", 0)
                status = tp.get("status", "?")
                control = "Enabled" if tp.get("control_enabled") else "Disabled (need fan_control=1)"
                info = (
                    f"Status: {status} | Speed: {speed} RPM | Level: {level}\n"
                    f"Control: {control}"
                )
                self.query_one("#tp-status", Static).update(info)
        except Exception:
            pass
