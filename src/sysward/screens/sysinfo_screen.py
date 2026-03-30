"""System information tab — static hardware/OS details."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static


class SysInfoScreen(Vertical):
    """System information display."""

    DEFAULT_CSS = """
    SysInfoScreen {
        height: 1fr;
        padding: 1;
    }
    SysInfoScreen .sysinfo-section {
        height: auto;
        padding: 1 2;
        margin-bottom: 1;
        border: round $panel;
        background: $surface;
    }
    SysInfoScreen .sysinfo-title {
        color: $primary;
        text-style: bold;
        height: 1;
        margin-bottom: 1;
    }
    SysInfoScreen .sysinfo-content {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(classes="sysinfo-section"):
            yield Static("System", classes="sysinfo-title")
            yield Static("Loading...", id="sys-info", classes="sysinfo-content")
        with Vertical(classes="sysinfo-section"):
            yield Static("Hardware", classes="sysinfo-title")
            yield Static("Loading...", id="hw-info", classes="sysinfo-content")
        with Vertical(classes="sysinfo-section"):
            yield Static("Packages & Updates", classes="sysinfo-title")
            yield Static("Loading...", id="pkg-info", classes="sysinfo-content")

    def update_metrics(self, metrics: dict[str, Any], history: dict) -> None:
        sysinfo = metrics.get("sysinfo", {})
        if not sysinfo:
            return

        # System section
        sys_lines = [
            f"OS:        {sysinfo.get('os_release', '?')}",
            f"Kernel:    {sysinfo.get('kernel', '?')}",
            f"Hostname:  {sysinfo.get('hostname', '?')}",
            f"Uptime:    {sysinfo.get('uptime', '?')}",
            f"Boot:      {sysinfo.get('boot_time', '?')}",
        ]
        try:
            self.query_one("#sys-info", Static).update("\n".join(sys_lines))
        except Exception:
            pass

        # Hardware section
        hw_lines = [
            f"CPU:       {sysinfo.get('cpu_model', '?')}",
            f"RAM:       {sysinfo.get('ram_total_gb', 0)} GiB",
        ]
        for i, gpu in enumerate(sysinfo.get("gpu_info", [])):
            hw_lines.append(f"GPU {i}:     {gpu}")
        try:
            self.query_one("#hw-info", Static).update("\n".join(hw_lines))
        except Exception:
            pass

        # Packages section
        pkg_lines = [
            f"Installed: {sysinfo.get('package_count', 0)} packages",
        ]
        try:
            self.query_one("#pkg-info", Static).update("\n".join(pkg_lines))
        except Exception:
            pass
