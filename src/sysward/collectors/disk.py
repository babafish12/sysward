"""Disk collector — /proc/diskstats + os.statvfs()."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sysward.collectors.base import BaseCollector

_DISKSTATS = Path("/proc/diskstats")
_SECTOR_SIZE = 512  # bytes


class DiskCollector(BaseCollector):
    def __init__(self) -> None:
        self._prev_stats: dict[str, tuple[int, int]] = {}  # dev -> (read_sectors, write_sectors)

    def is_available(self) -> bool:
        return _DISKSTATS.exists()

    def collect(self) -> dict[str, Any]:
        data: dict[str, Any] = {}

        # Filesystem usage
        data["filesystems"] = self._collect_filesystems()

        # I/O stats from /proc/diskstats
        data["devices"] = self._collect_io()

        return data

    def _collect_filesystems(self) -> list[dict[str, Any]]:
        filesystems: list[dict[str, Any]] = []
        seen: set[str] = set()

        mounts = Path("/proc/mounts").read_text().splitlines()
        for line in mounts:
            parts = line.split()
            if len(parts) < 4:
                continue
            device, mount, fstype = parts[0], parts[1], parts[2]
            # Only real filesystems
            if fstype in ("proc", "sysfs", "devtmpfs", "devpts", "tmpfs",
                          "securityfs", "cgroup", "cgroup2", "pstore",
                          "bpf", "tracefs", "debugfs", "hugetlbfs",
                          "mqueue", "fusectl", "configfs", "efivarfs",
                          "autofs", "ramfs", "fuse.portal"):
                continue
            if device in seen:
                continue
            seen.add(device)

            try:
                st = os.statvfs(mount)
                total = st.f_blocks * st.f_frsize
                free = st.f_bfree * st.f_frsize
                avail = st.f_bavail * st.f_frsize
                used = total - free
                percent = (used / total * 100) if total > 0 else 0.0
                filesystems.append({
                    "device": device,
                    "mount": mount,
                    "fstype": fstype,
                    "total": total,
                    "used": used,
                    "avail": avail,
                    "percent": percent,
                })
            except OSError:
                pass

        return filesystems

    def _collect_io(self) -> list[dict[str, Any]]:
        devices: list[dict[str, Any]] = []

        for line in _DISKSTATS.read_text().splitlines():
            parts = line.split()
            if len(parts) < 14:
                continue
            dev_name = parts[2]
            # Only whole disks (nvme0n1, sda) not partitions
            if dev_name[-1].isdigit() and not dev_name.startswith("nvme"):
                continue
            if "p" in dev_name and dev_name.startswith("nvme"):
                # Skip nvme partitions like nvme0n1p1
                if dev_name.count("p") > 0 and dev_name.split("p")[-1].isdigit():
                    # nvme0n1p1 -> skip, nvme0n1 -> keep
                    if "n" in dev_name:
                        after_n = dev_name.split("n", 1)[1]
                        if "p" in after_n:
                            continue

            read_sectors = int(parts[5])
            write_sectors = int(parts[9])

            read_bytes_s = 0.0
            write_bytes_s = 0.0
            if dev_name in self._prev_stats:
                prev_r, prev_w = self._prev_stats[dev_name]
                read_bytes_s = (read_sectors - prev_r) * _SECTOR_SIZE
                write_bytes_s = (write_sectors - prev_w) * _SECTOR_SIZE

            self._prev_stats[dev_name] = (read_sectors, write_sectors)

            devices.append({
                "name": dev_name,
                "read_bytes_s": read_bytes_s,
                "write_bytes_s": write_bytes_s,
            })

        return devices
