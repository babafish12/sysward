"""Metric export — CSV and JSON formats."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sysward.models.history import RingBuffer


def export_csv(history: dict[str, RingBuffer], path: Path) -> int:
    """Export all history to CSV. Returns number of rows written."""
    rows = 0
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "metric_name", "value"])
        for name, buf in sorted(history.items()):
            for ts, val in buf.last_n_with_time(buf.maxlen):
                dt = datetime.fromtimestamp(ts).isoformat()
                writer.writerow([dt, name, f"{val:.2f}"])
                rows += 1
    return rows


def export_json(history: dict[str, RingBuffer], path: Path) -> int:
    """Export all history to JSON. Returns number of snapshots written."""
    snapshots: list[dict[str, Any]] = []
    for name, buf in sorted(history.items()):
        for ts, val in buf.last_n_with_time(buf.maxlen):
            snapshots.append({
                "timestamp": datetime.fromtimestamp(ts).isoformat(),
                "metric": name,
                "value": round(val, 2),
            })
    snapshots.sort(key=lambda x: x["timestamp"])
    with open(path, "w") as f:
        json.dump(snapshots, f, indent=2)
    return len(snapshots)
