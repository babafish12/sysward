"""Main Textual application — single screen with TabbedContent."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import TabbedContent, TabPane
from textual import work

from sysward.models.config import ConfigManager
from sysward.services.exporter import export_csv, export_json
from sysward.services.session_logger import SessionLogger
from sysward.models.profile import PerformanceProfile
from sysward.services.collector_manager import CollectorManager
from sysward.services.profile_manager import ProfileManager
from sysward.services.process_manager import ProcessManager
from sysward.services.alert_manager import AlertManager
from sysward.services.disk_cleaner import DiskCleanerService
from sysward.theme import THEMES, next_theme
from sysward.widgets.header_bar import HeaderBar
from sysward.widgets.hint_bar import HintBar
from sysward.screens.overview import OverviewScreen
from sysward.screens.cpu_detail import CPUDetailScreen
from sysward.screens.memory_detail import MemoryDetailScreen
from sysward.screens.disk_detail import DiskDetailScreen
from sysward.screens.network_detail import NetworkDetailScreen
from sysward.screens.process_screen import ProcessScreen
from sysward.screens.systemd_screen import SystemdScreen
from sysward.screens.cleaner_screen import CleanerScreen
from sysward.screens.sysinfo_screen import SysInfoScreen
from sysward.screens.fan_screen import FanScreen
from sysward.screens.profile_screen import ProfileScreen
from sysward.screens.confirm_dialog import ConfirmDialog
from sysward.services.fan_control import ThinkPadFanControl


class SyswardApp(App):
    CSS = """
    Screen {
        background: $background;
        color: $foreground;
    }
    TabbedContent {
        height: 1fr;
    }
    ContentSwitcher {
        height: 1fr;
    }
    TabPane {
        height: 1fr;
        padding: 0;
    }
    DataTable {
        background: $background;
        color: $foreground;
    }
    DataTable > .datatable--header {
        background: $surface;
        color: $primary;
        text-style: bold;
    }
    DataTable > .datatable--cursor {
        background: $panel;
        color: $foreground;
    }
    DataTable > .datatable--even-row {
        background: $background;
    }
    DataTable > .datatable--odd-row {
        background: $surface;
    }
    Input {
        background: $panel;
        color: $foreground;
        border: tall $panel;
    }
    Input:focus {
        border: tall $primary;
    }
    Button {
        background: $surface;
        color: $foreground;
        border: tall $panel;
    }
    Button:hover {
        background: $panel;
    }
    Button.-primary {
        background: $primary;
        color: $background;
    }
    Button.-error {
        background: $error;
        color: $background;
    }
    Sparkline {
        background: $surface;
    }
    Toast {
        background: $surface;
        color: $foreground;
    }
    """

    TITLE = "Sysward"

    BINDINGS = [
        Binding("1", "tab('overview')", "Overview", show=False, priority=True),
        Binding("2", "tab('cpu')", "CPU", show=False, priority=True),
        Binding("3", "tab('memory')", "Memory", show=False, priority=True),
        Binding("4", "tab('disk')", "Disk", show=False, priority=True),
        Binding("5", "tab('network')", "Network", show=False, priority=True),
        Binding("6", "tab('process')", "Processes", show=False, priority=True),
        Binding("7", "tab('systemd')", "Services", show=False, priority=True),
        Binding("8", "tab('cleaner')", "Cleaner", show=False, priority=True),
        Binding("9", "tab('sysinfo')", "SysInfo", show=False, priority=True),
        Binding("0", "tab('fan')", "Fans", show=False, priority=True),
        Binding("p", "profiles", "Profiles", show=False, priority=True),
        Binding("T", "cycle_theme", "Theme", show=False, priority=True),
        Binding("k", "kill_process", "Kill", show=False),
        Binding("s", "stop_process", "Stop", show=False),
        Binding("r", "resume_process", "Resume", show=False),
        Binding("b", "blacklist_process", "Blacklist", show=False),
        Binding("slash", "toggle_filter", "Filter", show=False),
        Binding("c", "clean_selected", "Clean", show=False),
        Binding("space", "toggle_clean_select", "Toggle", show=False),
        Binding("a", "select_all_clean", "All", show=False),
        Binding("n", "deselect_all_clean", "None", show=False),
        Binding("d", "show_clean_detail", "Detail", show=False),
        Binding("e", "export_metrics", "Export", show=False, priority=True),
        Binding("q", "quit_app", "Quit", show=False, priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config_manager = ConfigManager()
        self.collector_manager = CollectorManager()
        self.profile_manager = ProfileManager()
        self.process_manager = ProcessManager()
        self.alert_manager = AlertManager()
        self.disk_cleaner = DiskCleanerService()
        self.fan_control = ThinkPadFanControl()
        self._active_tab = "overview"
        self.session_logger = SessionLogger()

    def compose(self) -> ComposeResult:
        yield HeaderBar(id="header")
        with TabbedContent(id="tabs"):
            with TabPane("Overview", id="overview"):
                yield OverviewScreen(id="overview-screen")
            with TabPane("CPU", id="cpu"):
                yield CPUDetailScreen(id="cpu-screen")
            with TabPane("Memory", id="memory"):
                yield MemoryDetailScreen(id="memory-screen")
            with TabPane("Disk", id="disk"):
                yield DiskDetailScreen(id="disk-screen")
            with TabPane("Network", id="network"):
                yield NetworkDetailScreen(id="network-screen")
            with TabPane("Processes", id="process"):
                yield ProcessScreen(id="process-screen")
            with TabPane("Services", id="systemd"):
                yield SystemdScreen(id="systemd-screen")
            with TabPane("Cleaner", id="cleaner"):
                yield CleanerScreen(id="cleaner-screen")
            with TabPane("System", id="sysinfo"):
                yield SysInfoScreen(id="sysinfo-screen")
            with TabPane("Fans", id="fan"):
                yield FanScreen(id="fan-screen")
        yield HintBar(
            "[k]1-0[/k] Tabs  [k]p[/k] Profiles  [k]T[/k] Theme  [k]q[/k] Quit",
            id="hints",
        )

    def on_mount(self) -> None:
        # Load config
        self.config_manager.load()

        # Register themes
        for t in THEMES:
            self.register_theme(t)
        self.theme = self.config_manager.theme

        # Discover hardware
        available = self.collector_manager.discover()
        self.notify(f"Discovered: {', '.join(sorted(available))}", timeout=3)

        # Check for stale fan lock from previous crash
        self.fan_control.check_stale_lock()

        # Detect current profile
        profile = self.profile_manager.detect_current()
        if profile:
            self.query_one("#header", HeaderBar).update_info(
                profile=profile.replace("_", " ").title()
            )

        # Pass cleaner config
        self.disk_cleaner.update_config(self.config_manager.cleaner)

        # Start collection loops
        self._run_fast_collector()
        self._run_slow_collector()

        # Start session logger if enabled
        if self.config_manager.session_logging_enabled:
            log_cfg = self.config_manager.logging_config
            self.session_logger = SessionLogger(
                log_dir=log_cfg.get("log_dir", "~/.local/share/sysward/logs"),
                max_size_mb=log_cfg.get("max_log_size_mb", 5),
                interval=log_cfg.get("session_log_interval", 5.0),
            )
            self.session_logger.start()

    @work(thread=True)
    def _run_fast_collector(self) -> None:
        """Fast collection loop — CPU, RAM, GPU, sensors, network, battery (1s)."""
        interval = self.config_manager.refresh_fast
        while not self.collector_manager._stop.is_set():
            try:
                self.collector_manager.collect_fast()
                self.call_from_thread(self._update_ui)
                self.session_logger.append(self.collector_manager.metrics)
                # Check alerts
                metrics = self.collector_manager.metrics
                alerts = self.alert_manager.check(metrics, self.config_manager.alerts)
                for alert in alerts:
                    self.call_from_thread(self.notify, alert, severity="warning", timeout=5)
                # Fan safety watchdog
                cpu_temp = metrics.get("sensors", {}).get("package_temp", 0)
                safety_limit = self.config_manager.fan_control_config.get("safety_temp_limit", 90)
                if self.fan_control.check_safety(cpu_temp, safety_limit):
                    self.call_from_thread(
                        self.notify, f"Fan forced to full-speed (temp {cpu_temp:.0f}°C)",
                        severity="warning", timeout=10,
                    )
            except Exception:
                pass
            self.collector_manager._stop.wait(interval)

    @work(thread=True)
    def _run_slow_collector(self) -> None:
        """Slow collection loop — processes, systemd, disk (5s)."""
        interval = self.config_manager.refresh_slow
        while not self.collector_manager._stop.is_set():
            try:
                self.collector_manager.collect_slow()
                # Enforce blacklist
                actions = self.process_manager.enforce_blacklist(
                    self.config_manager.blacklist
                )
                for action in actions:
                    self.call_from_thread(self.notify, action, timeout=3)
                self.call_from_thread(self._update_ui)
            except Exception:
                pass
            self.collector_manager._stop.wait(interval)

    # Tab ID -> (widget selector, widget class) for dispatch.
    # Tabs without periodic updates (e.g. cleaner) are omitted.
    _TAB_REGISTRY: dict[str, tuple[str, type]] = {
        "overview": ("#overview-screen", OverviewScreen),
        "cpu": ("#cpu-screen", CPUDetailScreen),
        "memory": ("#memory-screen", MemoryDetailScreen),
        "disk": ("#disk-screen", DiskDetailScreen),
        "network": ("#network-screen", NetworkDetailScreen),
        "process": ("#process-screen", ProcessScreen),
        "systemd": ("#systemd-screen", SystemdScreen),
        "sysinfo": ("#sysinfo-screen", SysInfoScreen),
        "fan": ("#fan-screen", FanScreen),
    }

    def _update_ui(self) -> None:
        """Update only the active tab's content."""
        metrics = self.collector_manager.metrics
        history = self.collector_manager.history

        # Always update header uptime
        profile = self.profile_manager.active_profile
        self.query_one("#header", HeaderBar).update_info(
            profile=profile.replace("_", " ").title() if profile else "Unknown"
        )

        # Update active tab via registry
        active = self.query_one("#tabs", TabbedContent).active
        entry = self._TAB_REGISTRY.get(active)
        if entry:
            try:
                selector, cls = entry
                self.query_one(selector, cls).update_metrics(metrics, history)
            except Exception:
                pass

    # --- Actions ---

    def action_tab(self, tab_id: str) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = tab_id

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Sync _active_tab on any tab change (keyboard, click, or programmatic)."""
        tab_id = event.pane.id or ""
        self._active_tab = tab_id
        hints = self.query_one("#hints", HintBar)
        if tab_id == "process":
            hints.set_hints(
                "[k]k[/k] Kill  [k]s[/k] Stop  [k]r[/k] Resume  [k]b[/k] Blacklist  [k]/[/k] Filter  [k]1-0[/k] Tabs"
            )
        elif tab_id == "systemd":
            hints.set_hints("[k]/[/k] Filter  [k]1-0[/k] Tabs  [k]p[/k] Profiles  [k]q[/k] Quit")
        elif tab_id == "cleaner":
            hints.set_hints(
                "[k]s[/k] Scan  [k]Space[/k] Toggle  [k]a[/k] All  [k]n[/k] None  [k]c[/k] Clean  [k]d[/k] Detail  [k]1-0[/k] Tabs"
            )
        else:
            hints.set_hints("[k]1-0[/k] Tabs  [k]p[/k] Profiles  [k]T[/k] Theme  [k]q[/k] Quit")

    def action_profiles(self) -> None:
        profiles = self.config_manager.profiles
        active = self.profile_manager.active_profile

        def on_profile(name: str | None) -> None:
            if name is None:
                return
            profile_data = self.config_manager.get_profile(name)
            if not profile_data:
                self.notify(f"Profile '{name}' not found", severity="error")
                return
            profile = PerformanceProfile.from_dict(name, profile_data)
            ok, msg = self.profile_manager.apply(profile)
            if ok:
                self.notify(msg, severity="information", timeout=3)
                self.query_one("#header", HeaderBar).update_info(
                    profile=profile.display_name
                )
            else:
                self.notify(f"Failed: {msg}", severity="error", timeout=5)

        self.push_screen(ProfileScreen(profiles, active), callback=on_profile)

    def action_cycle_theme(self) -> None:
        new = next_theme(self.theme)
        self.theme = new
        self.config_manager.theme = new
        self.config_manager.save()
        self.query_one("#hints", HintBar).refresh_hints()

    def action_kill_process(self) -> None:
        if self._active_tab != "process":
            return
        pid = self.query_one("#process-screen", ProcessScreen).get_selected_pid()
        if pid is None:
            self.notify("No process selected", severity="warning")
            return

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                ok, msg = self.process_manager.kill_process(pid)
                self.notify(msg, severity="information" if ok else "error")

        self.push_screen(
            ConfirmDialog("Kill Process", f"Send SIGTERM to PID {pid}?"),
            callback=on_confirm,
        )

    def action_stop_process(self) -> None:
        if self._active_tab == "cleaner":
            self._start_scan()
            return
        if self._active_tab != "process":
            return
        pid = self.query_one("#process-screen", ProcessScreen).get_selected_pid()
        if pid is None:
            self.notify("No process selected", severity="warning")
            return
        ok, msg = self.process_manager.stop_process(pid)
        self.notify(msg, severity="information" if ok else "error")

    def action_resume_process(self) -> None:
        if self._active_tab != "process":
            return
        pid = self.query_one("#process-screen", ProcessScreen).get_selected_pid()
        if pid is None:
            self.notify("No process selected", severity="warning")
            return
        ok, msg = self.process_manager.resume_process(pid)
        self.notify(msg, severity="information" if ok else "error")

    def action_blacklist_process(self) -> None:
        if self._active_tab != "process":
            return
        pid = self.query_one("#process-screen", ProcessScreen).get_selected_pid()
        if pid is None:
            self.notify("No process selected", severity="warning")
            return
        # Find process name
        metrics = self.collector_manager.metrics
        procs = metrics.get("process", {}).get("processes", [])
        name = None
        for p in procs:
            if p.get("pid") == pid:
                name = p.get("name")
                break
        if not name:
            self.notify("Process not found", severity="error")
            return

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                self.config_manager.add_to_blacklist(name, "stop")
                self.notify(f"Added '{name}' to blacklist (stop)")

        self.push_screen(
            ConfirmDialog("Add to Blacklist", f"Add '{name}' to blacklist with SIGSTOP action?"),
            callback=on_confirm,
        )

    def action_toggle_filter(self) -> None:
        if self._active_tab == "process":
            self.query_one("#process-screen", ProcessScreen).toggle_filter()
        elif self._active_tab == "systemd":
            self.query_one("#systemd-screen", SystemdScreen).toggle_filter()

    # --- Cleaner actions ---

    def _start_scan(self) -> None:
        """Initiate scan from the main thread, then run heavy work in worker."""
        screen = self.query_one("#cleaner-screen", CleanerScreen)
        if screen.is_scanning:
            return
        screen.set_scanning()
        self._run_scan()

    @work(thread=True)
    def _run_scan(self) -> None:
        results = self.disk_cleaner.scan_all()
        self.call_from_thread(self._finish_scan, results)

    def _finish_scan(self, results: list) -> None:
        """Handle scan results on the main thread."""
        screen = self.query_one("#cleaner-screen", CleanerScreen)
        screen.set_scan_results(results)
        self.notify(
            f"Scan complete: {len(results)} categories found",
            severity="information",
            timeout=3,
        )

    def action_toggle_clean_select(self) -> None:
        if self._active_tab != "cleaner":
            return
        screen = self.query_one("#cleaner-screen", CleanerScreen)
        if screen.is_detail_focused:
            screen.toggle_detail_item()
        else:
            screen.toggle_select()

    def action_select_all_clean(self) -> None:
        if self._active_tab != "cleaner":
            return
        screen = self.query_one("#cleaner-screen", CleanerScreen)
        if screen.is_detail_focused:
            screen.select_all_detail_items()
        else:
            screen.select_all()

    def action_deselect_all_clean(self) -> None:
        if self._active_tab != "cleaner":
            return
        screen = self.query_one("#cleaner-screen", CleanerScreen)
        if screen.is_detail_focused:
            screen.deselect_all_detail_items()
        else:
            screen.deselect_all()

    def action_show_clean_detail(self) -> None:
        if self._active_tab != "cleaner":
            return
        self.query_one("#cleaner-screen", CleanerScreen).toggle_detail()

    def action_clean_selected(self) -> None:
        if self._active_tab != "cleaner":
            return
        screen = self.query_one("#cleaner-screen", CleanerScreen)
        selected = screen.get_selected_categories()
        if not selected:
            self.notify("No categories selected", severity="warning")
            return

        total_bytes = screen.get_selected_total_bytes()
        effective_results = screen.get_effective_scan_results()
        root_cats = [
            r.display_name for r in effective_results
            if r.category_id in selected and r.needs_root
        ]

        # Build confirmation message
        from sysward.widgets.cleaner_table import _fmt_bytes
        msg = f"Clean {len(selected)} categories?\nEstimated space: {_fmt_bytes(total_bytes)}"
        if root_cats:
            msg += f"\n\nRoot required for:\n- " + "\n- ".join(root_cats)
            msg += "\n\npkexec will prompt for authentication."

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                self._start_clean(selected, effective_results)

        self.push_screen(
            ConfirmDialog("Disk Cleanup", msg),
            callback=on_confirm,
        )

    def _start_clean(self, selected: set[str], scan_results: list) -> None:
        """Initiate clean from the main thread, then run heavy work in worker."""
        screen = self.query_one("#cleaner-screen", CleanerScreen)
        screen.set_cleaning()
        self._run_clean(selected, scan_results)

    @work(thread=True)
    def _run_clean(self, selected: set[str], scan_results: list) -> None:
        outcomes = self.disk_cleaner.clean(selected, scan_results)
        total_freed = sum(freed for _, ok, freed, _ in outcomes if ok)
        failed = [msg for _, ok, _, msg in outcomes if not ok]
        # Auto re-scan
        results = self.disk_cleaner.scan_all()
        self.call_from_thread(self._finish_clean, total_freed, failed, results)

    def _finish_clean(self, total_freed: int, failed: list, results: list) -> None:
        """Handle clean results on the main thread."""
        screen = self.query_one("#cleaner-screen", CleanerScreen)
        from sysward.widgets.cleaner_table import _fmt_bytes
        if failed:
            summary = f"Freed {_fmt_bytes(total_freed)} | {len(failed)} failed"
            screen.set_clean_done(summary)
            self.notify(summary, severity="warning", timeout=5)
        else:
            summary = f"Freed {_fmt_bytes(total_freed)}"
            screen.set_clean_done(summary)
            self.notify(summary, severity="information", timeout=3)
        screen.set_scan_results(results)

    def action_export_metrics(self) -> None:
        """Export metrics history to file."""
        from datetime import datetime
        from pathlib import Path
        history = self.collector_manager.history
        if not any(len(buf) > 0 for buf in history.values()):
            self.notify("No data to export yet", severity="warning")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = Path(self.config_manager.export_dir).expanduser()
        export_dir.mkdir(parents=True, exist_ok=True)
        fmt = self.config_manager.export_format
        if fmt == "json":
            path = export_dir / f"sysward-{ts}.json"
            count = export_json(history, path)
        else:
            path = export_dir / f"sysward-{ts}.csv"
            count = export_csv(history, path)
        self.notify(f"Exported {count} records to {path}", timeout=5)

    # --- Fan control actions ---

    def action_set_fan_level(self, level: str) -> None:
        if self._active_tab != "fan":
            return
        if not self.config_manager.fan_control_enabled:
            self.notify("Fan control disabled in config", severity="warning")
            return

        def on_confirm(confirmed: bool) -> None:
            if confirmed:
                ok, msg = self.fan_control.set_level(level)
                self.notify(msg, severity="information" if ok else "error")

        self.push_screen(
            ConfirmDialog("Fan Control", f"Set fan level to '{level}'?"),
            callback=on_confirm,
        )

    def action_quit_app(self) -> None:
        self.fan_control.reset_to_auto()
        self.session_logger.stop()
        self.collector_manager.stop()
        self.exit()

    def on_unmount(self) -> None:
        self.fan_control.reset_to_auto()
        self.session_logger.stop()
        self.collector_manager.stop()
