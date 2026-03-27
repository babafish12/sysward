"""Data models for disk cleaner scan results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CleanItem:
    """A single file or package that can be cleaned."""

    path: str
    size: int
    description: str


@dataclass
class ScanResult:
    """Scan result for one cleanup category."""

    category_id: str
    display_name: str
    total_bytes: int
    items: list[CleanItem] = field(default_factory=list)
    needs_root: bool = False
    item_label: str = ""  # e.g. "47 packages", "23 files"
