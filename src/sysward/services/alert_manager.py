"""Alert manager — threshold checks + notify-send."""

from __future__ import annotations

import subprocess
import time
from typing import Any


class AlertManager:
    def __init__(self) -> None:
        self._last_alert: dict[str, float] = {}  # alert_key -> timestamp
        self._temp_history: list[tuple[float, float]] = []

    def check(self, metrics: dict[str, Any], config: dict) -> list[str]:
        """Check metrics against thresholds. Returns list of triggered alerts."""
        if not config.get("enabled", True):
            return []

        cooldown = config.get("cooldown", 60)
        alerts: list[str] = []
        now = time.time()

        # CPU temperature
        pkg_temp = metrics.get("sensors", {}).get("package_temp", 0)
        if pkg_temp:
            crit = config.get("cpu_temp_crit", 95)
            warn = config.get("cpu_temp_warn", 80)
            if pkg_temp >= crit:
                alerts.extend(self._fire("cpu_temp_crit", f"CPU CRITICAL: {pkg_temp:.0f}°C", "critical", cooldown, now))
            elif pkg_temp >= warn:
                alerts.extend(self._fire("cpu_temp_warn", f"CPU Temp: {pkg_temp:.0f}°C", "normal", cooldown, now))

        # CPU usage
        cpu_usage = metrics.get("cpu", {}).get("usage", 0)
        warn = config.get("cpu_usage_warn", 90)
        if cpu_usage >= warn:
            alerts.extend(self._fire("cpu_usage", f"CPU Usage: {cpu_usage:.0f}%", "normal", cooldown, now))

        # RAM usage
        ram_pct = metrics.get("memory", {}).get("usage_percent", 0)
        warn = config.get("ram_usage_warn", 85)
        if ram_pct >= warn:
            alerts.extend(self._fire("ram_usage", f"RAM Usage: {ram_pct:.0f}%", "normal", cooldown, now))

        # Battery
        bat_cap = metrics.get("battery", {}).get("capacity", 100)
        bat_status = metrics.get("battery", {}).get("status", "")
        if bat_status == "Discharging":
            crit = config.get("battery_critical", 10)
            low = config.get("battery_low", 20)
            if bat_cap <= crit:
                alerts.extend(self._fire("bat_crit", f"Battery CRITICAL: {bat_cap}%", "critical", cooldown, now))
            elif bat_cap <= low:
                alerts.extend(self._fire("bat_low", f"Battery Low: {bat_cap}%", "normal", cooldown, now))

        # Fan failure
        fan_rpm = metrics.get("sensors", {}).get("fan_rpm", 0)
        pkg_temp = metrics.get("sensors", {}).get("package_temp", 0)
        fan_failure_enabled = config.get("fan_failure_enabled", True)
        if fan_failure_enabled and fan_rpm == 0 and pkg_temp > 60:
            alerts.extend(self._fire("fan_failure", f"Fan STOPPED at {pkg_temp:.0f}°C!", "critical", cooldown, now))

        # Rapid temperature rise
        self._temp_history.append((now, pkg_temp))
        # Keep only last 60s of data
        self._temp_history = [(t, v) for t, v in self._temp_history if now - t < 60]
        temp_rise_warn = config.get("temp_rise_rate_warn", 10)
        if len(self._temp_history) >= 2:
            oldest_t, oldest_v = self._temp_history[0]
            if now - oldest_t >= 5 and pkg_temp - oldest_v >= temp_rise_warn:
                rate = (pkg_temp - oldest_v) / (now - oldest_t) * 30
                alerts.extend(self._fire("temp_rise", f"Rapid temp rise: {rate:.0f}°C/30s", "normal", cooldown, now))

        return alerts

    def _fire(self, key: str, message: str, urgency: str, cooldown: int, now: float) -> list[str]:
        if now - self._last_alert.get(key, 0) < cooldown:
            return []
        self._last_alert[key] = now
        self._notify(message, urgency)
        return [message]

    def _notify(self, message: str, urgency: str = "normal") -> None:
        """Send desktop notification via notify-send."""
        try:
            subprocess.run(
                ["notify-send", "-u", urgency, "-a", "Sysward", "Sysward", message],
                capture_output=True, timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
