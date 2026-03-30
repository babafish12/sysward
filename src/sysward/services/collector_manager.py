"""Collector manager — orchestrates all collectors in a background thread."""

from __future__ import annotations

import threading
import time
from typing import Any

from sysward.collectors.cpu import CPUCollector
from sysward.collectors.memory import MemoryCollector
from sysward.collectors.gpu import GPUCollector
from sysward.collectors.battery import BatteryCollector
from sysward.collectors.sensors import SensorsCollector
from sysward.collectors.disk import DiskCollector
from sysward.collectors.network import NetworkCollector
from sysward.collectors.process import ProcessCollector
from sysward.collectors.systemd import SystemdCollector
from sysward.collectors.sysinfo import SysInfoCollector
from sysward.collectors.fan import FanCollector
from sysward.models.history import RingBuffer


# Collector categories
FAST_COLLECTORS = ["cpu", "memory", "gpu", "battery", "sensors", "network", "fan"]
SLOW_COLLECTORS = ["disk", "process", "systemd", "sysinfo"]


class CollectorManager:
    def __init__(self) -> None:
        self._collectors: dict[str, Any] = {}
        self._available: set[str] = set()
        self._metrics: dict[str, Any] = {}
        self._history: dict[str, RingBuffer] = {
            "cpu_usage": RingBuffer(),
            "ram_usage": RingBuffer(),
            "gpu_freq": RingBuffer(),
            "net_rx": RingBuffer(),
            "net_tx": RingBuffer(),
            "cpu_temp": RingBuffer(),
            "fan_rpm": RingBuffer(),
        }
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def discover(self) -> set[str]:
        """Discover and register available collectors."""
        candidates = {
            "cpu": CPUCollector(),
            "memory": MemoryCollector(),
            "gpu": GPUCollector(),
            "battery": BatteryCollector(),
            "sensors": SensorsCollector(),
            "disk": DiskCollector(),
            "network": NetworkCollector(),
            "process": ProcessCollector(),
            "systemd": SystemdCollector(),
            "sysinfo": SysInfoCollector(),
            "fan": FanCollector(),
        }
        for name, collector in candidates.items():
            try:
                if collector.is_available():
                    self._collectors[name] = collector
                    self._available.add(name)
            except Exception:
                pass

        return self._available

    @property
    def available(self) -> set[str]:
        return self._available

    @property
    def metrics(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._metrics)

    @property
    def history(self) -> dict[str, RingBuffer]:
        return self._history

    def collect_fast(self) -> dict[str, Any]:
        """Collect fast-cycle metrics (1s interval)."""
        results: dict[str, Any] = {}
        for name in FAST_COLLECTORS:
            if name in self._collectors:
                try:
                    results[name] = self._collectors[name].collect()
                except Exception:
                    pass

        # Update history
        cpu_usage = results.get("cpu", {}).get("usage", 0)
        self._history["cpu_usage"].push(cpu_usage)

        ram_pct = results.get("memory", {}).get("usage_percent", 0)
        self._history["ram_usage"].push(ram_pct)

        gpu_freq = results.get("gpu", {}).get("freq_cur", 0)
        self._history["gpu_freq"].push(gpu_freq)

        cpu_temp = results.get("sensors", {}).get("package_temp", 0)
        self._history["cpu_temp"].push(cpu_temp)

        fan_rpm = results.get("sensors", {}).get("fan_rpm", 0)
        if fan_rpm == 0:
            # Fallback to dedicated fan collector data
            fan_fans = results.get("fan", {}).get("fans", {})
            if fan_fans:
                fan_rpm = max(fan_fans.values())
        self._history["fan_rpm"].push(fan_rpm)

        # Net throughput
        ifaces = results.get("network", {}).get("interfaces", [])
        total_rx = sum(i.get("rx_rate", 0) for i in ifaces)
        total_tx = sum(i.get("tx_rate", 0) for i in ifaces)
        self._history["net_rx"].push(total_rx)
        self._history["net_tx"].push(total_tx)

        with self._lock:
            self._metrics.update(results)

        return results

    def collect_slow(self) -> dict[str, Any]:
        """Collect slow-cycle metrics (5s interval)."""
        results: dict[str, Any] = {}
        for name in SLOW_COLLECTORS:
            if name in self._collectors:
                try:
                    results[name] = self._collectors[name].collect()
                except Exception:
                    pass

        with self._lock:
            self._metrics.update(results)

        return results

    def stop(self) -> None:
        self._stop.set()
