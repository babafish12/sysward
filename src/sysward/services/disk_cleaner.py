"""Disk cleaner service — scans for reclaimable space and performs cleanup."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

from sysward.models.clean_item import CleanItem, ScanResult


def _fmt_count(n: int, singular: str, plural: str | None = None) -> str:
    p = plural or (singular + "s")
    return f"{n} {singular if n == 1 else p}"


def _dir_size(path: Path) -> int:
    """Recursively calculate directory size in bytes."""
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += _dir_size(Path(entry.path))
            except (PermissionError, OSError):
                continue
    except (PermissionError, OSError):
        pass
    return total


class DiskCleanerService:
    """On-demand scanner and cleaner for disk space recovery."""

    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}

    def update_config(self, config: dict) -> None:
        self._config = config

    @property
    def pacman_keep(self) -> int:
        return self._config.get("pacman_keep_versions", 2)

    @property
    def journal_max(self) -> str:
        return self._config.get("journal_max_size", "100M")

    @property
    def tmp_max_age_days(self) -> int:
        return self._config.get("tmp_max_age_days", 7)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan_all(self) -> list[ScanResult]:
        """Run all scanners and return results (sorted by size desc)."""
        scanners = [
            self._scan_pacman_cache,
            self._scan_orphans,
            self._scan_journal,
            self._scan_coredumps,
            self._scan_trash,
            self._scan_cache,
            self._scan_old_logs,
            self._scan_bak_files,
        ]
        results: list[ScanResult] = []
        for scanner in scanners:
            try:
                result = scanner()
                if result and result.total_bytes > 0:
                    results.append(result)
            except Exception:
                continue
        results.sort(key=lambda r: r.total_bytes, reverse=True)
        return results

    def clean(
        self, category_ids: set[str], scan_results: list[ScanResult]
    ) -> list[tuple[str, bool, int, str]]:
        """Clean selected categories. Returns list of (category_id, success, freed_bytes, message)."""
        results_map = {r.category_id: r for r in scan_results}
        outcomes: list[tuple[str, bool, int, str]] = []

        # Separate root and user operations
        root_ids = {cid for cid in category_ids if results_map.get(cid, ScanResult("", "", 0)).needs_root}
        user_ids = category_ids - root_ids

        # Execute user-level operations first
        for cid in user_ids:
            result = results_map.get(cid)
            if not result:
                continue
            try:
                freed = self._clean_category(cid, result)
                outcomes.append((cid, True, freed, f"{result.display_name}: OK"))
            except Exception as e:
                outcomes.append((cid, False, 0, f"{result.display_name}: {e}"))

        # Execute root operations in a single pkexec call
        if root_ids:
            root_outcomes = self._clean_root_categories(root_ids, results_map)
            outcomes.extend(root_outcomes)

        return outcomes

    # ------------------------------------------------------------------
    # Scanners
    # ------------------------------------------------------------------

    def _scan_pacman_cache(self) -> ScanResult | None:
        cache_dir = Path("/var/cache/pacman/pkg")
        if not cache_dir.exists():
            return None

        # Try paccache dry-run first
        if shutil.which("paccache"):
            try:
                proc = subprocess.run(
                    ["paccache", "-dk" + str(self.pacman_keep), "--nocolor"],
                    capture_output=True, text=True, timeout=30,
                )
                # paccache lists removable packages, one per line
                # Last line: "==> finished: N packages removed (disk space saved: X)"
                # Or lines like: /var/cache/pacman/pkg/package-version.pkg.tar.zst
                items: list[CleanItem] = []
                total = 0
                for line in proc.stdout.strip().splitlines():
                    line = line.strip()
                    if line.startswith("/var/cache/pacman/pkg/"):
                        p = Path(line)
                        try:
                            sz = p.stat().st_size
                            items.append(CleanItem(str(p), sz, p.name))
                            total += sz
                        except OSError:
                            continue
                if items:
                    return ScanResult(
                        category_id="pacman_cache",
                        display_name="Pacman Cache",
                        total_bytes=total,
                        items=sorted(items, key=lambda i: i.size, reverse=True),
                        needs_root=True,
                        item_label=_fmt_count(len(items), "package"),
                    )
            except (subprocess.TimeoutExpired, OSError):
                pass

        # Fallback: manually find old versions
        return self._scan_pacman_cache_manual(cache_dir)

    def _scan_pacman_cache_manual(self, cache_dir: Path) -> ScanResult | None:
        """Group packages by name and find versions beyond keep threshold."""
        packages: dict[str, list[tuple[str, Path]]] = defaultdict(list)
        # Package filenames: name-version-rel-arch.pkg.tar.zst
        pkg_re = re.compile(r"^(.+?)-(\d[^-]*-\d+)-([^-]+)\.pkg\.tar(?:\.\w+)?$")
        try:
            for entry in os.scandir(cache_dir):
                if not entry.is_file():
                    continue
                m = pkg_re.match(entry.name)
                if m:
                    pkg_name = m.group(1)
                    version = m.group(2)
                    packages[pkg_name].append((version, Path(entry.path)))
        except PermissionError:
            return None

        items: list[CleanItem] = []
        total = 0
        keep = self.pacman_keep
        for pkg_name, versions in packages.items():
            # Sort by version string (lexicographic is imperfect but reasonable)
            versions.sort(key=lambda v: v[0], reverse=True)
            for _ver, path in versions[keep:]:
                try:
                    sz = path.stat().st_size
                    items.append(CleanItem(str(path), sz, path.name))
                    total += sz
                except OSError:
                    continue

        if not items:
            return None
        return ScanResult(
            category_id="pacman_cache",
            display_name="Pacman Cache",
            total_bytes=total,
            items=sorted(items, key=lambda i: i.size, reverse=True),
            needs_root=True,
            item_label=_fmt_count(len(items), "package"),
        )

    def _scan_orphans(self) -> ScanResult | None:
        try:
            proc = subprocess.run(
                ["pacman", "-Qdtq"],
                capture_output=True, text=True, timeout=15,
            )
            if proc.returncode != 0 or not proc.stdout.strip():
                return None
            orphan_names = proc.stdout.strip().splitlines()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

        # Get sizes via pacman -Qi
        items: list[CleanItem] = []
        total = 0
        for name in orphan_names:
            size = self._get_package_size(name.strip())
            items.append(CleanItem(name.strip(), size, name.strip()))
            total += size

        if not items:
            return None
        return ScanResult(
            category_id="orphans",
            display_name="Orphaned Packages",
            total_bytes=total,
            items=sorted(items, key=lambda i: i.size, reverse=True),
            needs_root=True,
            item_label=_fmt_count(len(items), "package"),
        )

    def _get_package_size(self, name: str) -> int:
        """Get installed size of a package via pacman -Qi."""
        try:
            proc = subprocess.run(
                ["pacman", "-Qi", name],
                capture_output=True, text=True, timeout=5,
            )
            for line in proc.stdout.splitlines():
                if line.startswith("Installed Size"):
                    # Format: "Installed Size  : 1234.56 KiB"
                    parts = line.split(":")
                    if len(parts) >= 2:
                        size_str = parts[1].strip()
                        return self._parse_size(size_str)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return 0

    @staticmethod
    def _parse_size(size_str: str) -> int:
        """Parse human-readable size like '1.23 MiB' to bytes."""
        m = re.match(r"([\d.]+)\s*(\w+)", size_str)
        if not m:
            return 0
        val = float(m.group(1))
        unit = m.group(2).lower()
        multipliers = {
            "b": 1, "bytes": 1,
            "kib": 1024, "kb": 1000,
            "mib": 1024**2, "mb": 1000**2,
            "gib": 1024**3, "gb": 1000**3,
            "tib": 1024**4, "tb": 1000**4,
        }
        return int(val * multipliers.get(unit, 1))

    def _scan_journal(self) -> ScanResult | None:
        try:
            proc = subprocess.run(
                ["journalctl", "--disk-usage"],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode != 0:
                return None
            # Output: "Archived and active journals take up 1.2G on disk."
            m = re.search(r"([\d.]+)([KMGT])", proc.stdout)
            if not m:
                return None
            val = float(m.group(1))
            unit = m.group(2)
            multipliers = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
            current_bytes = int(val * multipliers.get(unit, 1))

            # Calculate how much exceeds the configured max
            max_bytes = self._parse_size(self.journal_max)
            reclaimable = max(0, current_bytes - max_bytes)
            if reclaimable <= 0:
                return None

            return ScanResult(
                category_id="journal",
                display_name="Journal Logs",
                total_bytes=reclaimable,
                items=[CleanItem("/var/log/journal", reclaimable, f"Vacuum to {self.journal_max}")],
                needs_root=True,
                item_label=f"over {self.journal_max}",
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    def _scan_coredumps(self) -> ScanResult | None:
        dump_dir = Path("/var/lib/systemd/coredump")
        if not dump_dir.exists():
            return None
        items: list[CleanItem] = []
        total = 0
        try:
            for entry in os.scandir(dump_dir):
                if entry.is_file(follow_symlinks=False):
                    try:
                        sz = entry.stat(follow_symlinks=False).st_size
                        items.append(CleanItem(entry.path, sz, entry.name))
                        total += sz
                    except OSError:
                        continue
        except PermissionError:
            # Try to get size via coredumpctl
            try:
                proc = subprocess.run(
                    ["coredumpctl", "list", "--no-pager"],
                    capture_output=True, text=True, timeout=10,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    lines = [l for l in proc.stdout.strip().splitlines() if l and not l.startswith("TIME")]
                    if lines:
                        # We can't get exact sizes easily, estimate from du
                        proc2 = subprocess.run(
                            ["du", "-sb", str(dump_dir)],
                            capture_output=True, text=True, timeout=5,
                        )
                        if proc2.returncode == 0:
                            parts = proc2.stdout.strip().split()
                            total = int(parts[0]) if parts else 0
                            items = [CleanItem(str(dump_dir), total, f"{len(lines)} coredumps")]
            except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
                return None

        if not items:
            return None
        return ScanResult(
            category_id="coredumps",
            display_name="Coredumps",
            total_bytes=total,
            items=sorted(items, key=lambda i: i.size, reverse=True),
            needs_root=True,
            item_label=_fmt_count(len(items), "dump"),
        )

    def _scan_trash(self) -> ScanResult | None:
        trash_dir = Path.home() / ".local" / "share" / "Trash"
        files_dir = trash_dir / "files"
        if not files_dir.exists():
            return None

        items: list[CleanItem] = []
        total = 0
        try:
            for entry in os.scandir(files_dir):
                try:
                    if entry.is_dir(follow_symlinks=False):
                        sz = _dir_size(Path(entry.path))
                    else:
                        sz = entry.stat(follow_symlinks=False).st_size
                    items.append(CleanItem(entry.path, sz, entry.name))
                    total += sz
                except OSError:
                    continue
        except (PermissionError, OSError):
            return None

        # Also count info dir
        info_dir = trash_dir / "info"
        if info_dir.exists():
            total += _dir_size(info_dir)

        if not items:
            return None
        return ScanResult(
            category_id="trash",
            display_name="Trash",
            total_bytes=total,
            items=sorted(items, key=lambda i: i.size, reverse=True),
            needs_root=False,
            item_label=_fmt_count(len(items), "file"),
        )

    def _scan_cache(self) -> ScanResult | None:
        cache_dir = Path.home() / ".cache"
        if not cache_dir.exists():
            return None

        items: list[CleanItem] = []
        total = 0
        try:
            for entry in os.scandir(cache_dir):
                if not entry.is_dir(follow_symlinks=False):
                    continue
                try:
                    sz = _dir_size(Path(entry.path))
                    if sz > 0:
                        items.append(CleanItem(entry.path, sz, entry.name))
                        total += sz
                except OSError:
                    continue
        except (PermissionError, OSError):
            return None

        if not items:
            return None
        return ScanResult(
            category_id="cache",
            display_name="User Cache",
            total_bytes=total,
            items=sorted(items, key=lambda i: i.size, reverse=True),
            needs_root=False,
            item_label=_fmt_count(len(items), "director", "directories"),
        )

    def _scan_old_logs(self) -> ScanResult | None:
        log_dir = Path("/var/log")
        if not log_dir.exists():
            return None

        items: list[CleanItem] = []
        total = 0
        patterns = ("*.old", "*.gz", "*.xz", "*.bz2", "*.zst", "*.[0-9]", "*.[0-9].gz")
        seen: set[str] = set()
        for pattern in patterns:
            try:
                for p in log_dir.rglob(pattern):
                    if str(p) in seen or not p.is_file():
                        continue
                    seen.add(str(p))
                    try:
                        sz = p.stat().st_size
                        items.append(CleanItem(str(p), sz, str(p.relative_to(log_dir))))
                        total += sz
                    except OSError:
                        continue
            except PermissionError:
                continue

        if not items:
            return None
        return ScanResult(
            category_id="old_logs",
            display_name="Old Logs",
            total_bytes=total,
            items=sorted(items, key=lambda i: i.size, reverse=True),
            needs_root=True,
            item_label=_fmt_count(len(items), "file"),
        )

    def _scan_bak_files(self) -> ScanResult | None:
        home = Path.home()
        items: list[CleanItem] = []
        total = 0
        extensions = {".bak", ".old", ".tmp"}
        skip_dirs = {".cache", ".local", ".git", ".venv", "venv", "node_modules", "__pycache__", ".cargo", ".rustup"}
        max_depth = 4

        def _walk(directory: Path, depth: int) -> None:
            nonlocal total
            if depth > max_depth:
                return
            try:
                for entry in os.scandir(directory):
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            name = entry.name
                            if name in skip_dirs or (depth == 0 and name.startswith(".")):
                                continue
                            _walk(Path(entry.path), depth + 1)
                        elif entry.is_file(follow_symlinks=False):
                            name = entry.name
                            if name.endswith("~") or any(name.endswith(ext) for ext in extensions):
                                sz = entry.stat(follow_symlinks=False).st_size
                                rel = str(Path(entry.path).relative_to(home))
                                items.append(CleanItem(entry.path, sz, rel))
                                total += sz
                    except OSError:
                        continue
            except (PermissionError, OSError):
                return

        _walk(home, 0)

        if not items:
            return None
        return ScanResult(
            category_id="bak_files",
            display_name="Backup/Temp Files",
            total_bytes=total,
            items=sorted(items, key=lambda i: i.size, reverse=True),
            needs_root=False,
            item_label=_fmt_count(len(items), "file"),
        )

    # ------------------------------------------------------------------
    # Cleaners
    # ------------------------------------------------------------------

    def _clean_category(self, category_id: str, result: ScanResult) -> int:
        """Clean a user-level category. Returns bytes freed."""
        if category_id == "trash":
            return self._clean_trash()
        elif category_id == "cache":
            return self._clean_cache(result)
        elif category_id == "bak_files":
            return self._clean_bak_files(result)
        return 0

    def _clean_trash(self) -> int:
        trash_dir = Path.home() / ".local" / "share" / "Trash"
        freed = 0
        for sub in ("files", "info", "expunged"):
            d = trash_dir / sub
            if d.exists():
                freed += _dir_size(d)
                shutil.rmtree(d, ignore_errors=True)
                d.mkdir(exist_ok=True)
        return freed

    def _clean_cache(self, result: ScanResult) -> int:
        freed = 0
        for item in result.items:
            p = Path(item.path)
            if p.exists() and p.is_dir():
                sz = _dir_size(p)
                shutil.rmtree(p, ignore_errors=True)
                freed += sz
        return freed

    def _clean_bak_files(self, result: ScanResult) -> int:
        freed = 0
        for item in result.items:
            p = Path(item.path)
            try:
                if p.exists():
                    freed += p.stat().st_size
                    p.unlink()
            except OSError:
                continue
        return freed

    def _clean_root_categories(
        self, category_ids: set[str], results_map: dict[str, ScanResult]
    ) -> list[tuple[str, bool, int, str]]:
        """Execute root-level cleanup operations via pkexec."""
        outcomes: list[tuple[str, bool, int, str]] = []
        commands: list[str] = []
        ordered_ids: list[str] = []

        for cid in category_ids:
            result = results_map.get(cid)
            if not result:
                continue
            cmd = self._root_clean_command(cid, result)
            if cmd:
                commands.append(cmd)
                ordered_ids.append(cid)

        if not commands:
            return outcomes

        # Bundle all root commands into one pkexec call
        combined = " && ".join(commands)
        try:
            proc = subprocess.run(
                ["pkexec", "bash", "-c", combined],
                capture_output=True, text=True, timeout=120,
            )
            if proc.returncode == 0:
                for cid in ordered_ids:
                    r = results_map[cid]
                    outcomes.append((cid, True, r.total_bytes, f"{r.display_name}: OK"))
            else:
                err = proc.stderr.strip()[:200] if proc.stderr else "Unknown error"
                for cid in ordered_ids:
                    r = results_map[cid]
                    outcomes.append((cid, False, 0, f"{r.display_name}: {err}"))
        except subprocess.TimeoutExpired:
            for cid in ordered_ids:
                r = results_map[cid]
                outcomes.append((cid, False, 0, f"{r.display_name}: Timeout"))
        except FileNotFoundError:
            for cid in ordered_ids:
                r = results_map[cid]
                outcomes.append((cid, False, 0, f"{r.display_name}: pkexec not found"))

        return outcomes

    def _root_clean_command(self, category_id: str, result: ScanResult) -> str | None:
        """Build a shell command string for a root-level clean operation."""
        if category_id == "pacman_cache":
            keep = self.pacman_keep
            if shutil.which("paccache"):
                return f"paccache -rk{keep}"
            # Fallback: remove specific files
            files = " ".join(f"'{item.path}'" for item in result.items)
            return f"rm -f {files}" if files else None

        elif category_id == "orphans":
            names = " ".join(item.path for item in result.items)
            return f"pacman --noconfirm -Rns {names}" if names else None

        elif category_id == "journal":
            return f"journalctl --vacuum-size={self.journal_max}"

        elif category_id == "coredumps":
            files = " ".join(f"'{item.path}'" for item in result.items)
            return f"rm -f {files}" if files else None

        elif category_id == "old_logs":
            files = " ".join(f"'{item.path}'" for item in result.items)
            return f"rm -f {files}" if files else None

        return None
