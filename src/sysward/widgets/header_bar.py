"""Header bar widget — hostname, uptime, active profile."""

from __future__ import annotations

import socket
from pathlib import Path

from textual.widgets import Static


def _get_uptime() -> str:
    try:
        seconds = float(Path("/proc/uptime").read_text().split()[0])
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except (OSError, ValueError):
        return "?"


def _get_cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                model = line.split(":", 1)[1].strip()
                # Shorten common prefixes
                for prefix in ("Intel(R) Core(TM) ", "AMD Ryzen "):
                    if model.startswith(prefix):
                        model = model[len("Intel(R) Core(TM) "):]  if "Intel" in prefix else model
                return model
        return "Unknown CPU"
    except OSError:
        return "Unknown CPU"


class HeaderBar(Static):
    """Top bar showing system info and active profile."""

    DEFAULT_CSS = """
    HeaderBar {
        dock: top;
        height: 1;
        background: $surface;
        color: $primary;
        text-style: bold;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._profile = "Detecting..."

    def on_mount(self) -> None:
        self.update_info()

    def update_info(self, profile: str | None = None) -> None:
        if profile is not None:
            self._profile = profile
        hostname = socket.gethostname()
        uptime = _get_uptime()
        cpu = _get_cpu_model()
        self.update(
            f" Sysward │ {hostname} │ {cpu} │ up {uptime} │ Profile: {self._profile}"
        )
