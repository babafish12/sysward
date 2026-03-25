"""Main Textual application — single screen with TabbedContent."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import TabbedContent, TabPane
from textual import work

from sysward.models.config import ConfigManager
from sysward.models.profile import PerformanceProfile
from sysward.services.collector_manager import CollectorManager
from sysward.services.profile_manager import ProfileManager
from sysward.services.process_manager import ProcessManager
from sysward.services.alert_manager import AlertManager
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
from sysward.screens.profile_screen import ProfileScreen
from sysward.screens.confirm_dialog import ConfirmDialog


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
        Binding("p", "profiles", "Profiles", show=False, priority=True),
        Binding("T", "cycle_theme", "Theme", show=False, priority=True),
        Binding("k", "kill_process", "Kill", show=False),
        Binding("s", "stop_process", "Stop", show=False),
        Binding("r", "resume_process", "Resume", show=False),
        Binding("b", "blacklist_process", "Blacklist", show=False),
        Binding("slash", "toggle_filter", "Filter", show=False),
        Binding("q", "quit_app", "Quit", show=False, priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config_manager = ConfigManager()
        self.collector_manager = CollectorManager()
        self.profile_manager = ProfileManager()
        self.process_manager = ProcessManager()
        self.alert_manager = AlertManager()
        self._active_tab = "overview"

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
        yield HintBar(
            "[k]1-7[/k] Tabs  [k]p[/k] Profiles  [k]T[/k] Theme  [k]q[/k] Quit",
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

        # Detect current profile
        profile = self.profile_manager.detect_current()
        if profile:
            self.query_one("#header", HeaderBar).update_info(
                profile=profile.replace("_", " ").title()
            )

        # Start collection loops
        self._run_fast_collector()
        self._run_slow_collector()

    @work(thread=True)
    def _run_fast_collector(self) -> None:
        """Fast collection loop — CPU, RAM, GPU, sensors, network, battery (1s)."""
        import time
        interval = self.config_manager.refresh_fast
        while not self.collector_manager._stop.is_set():
            try:
                self.collector_manager.collect_fast()
                self.call_from_thread(self._update_ui)
                # Check alerts
                metrics = self.collector_manager.metrics
                alerts = self.alert_manager.check(metrics, self.config_manager.alerts)
                for alert in alerts:
                    self.call_from_thread(self.notify, alert, severity="warning", timeout=5)
            except Exception:
                pass
            self.collector_manager._stop.wait(interval)

    @work(thread=True)
    def _run_slow_collector(self) -> None:
        """Slow collection loop — processes, systemd, disk (5s)."""
        import time
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

    def _update_ui(self) -> None:
        """Update only the active tab's content."""
        metrics = self.collector_manager.metrics
        history = self.collector_manager.history

        # Always update header uptime
        profile = self.profile_manager.active_profile
        self.query_one("#header", HeaderBar).update_info(
            profile=profile.replace("_", " ").title() if profile else "Unknown"
        )

        # Update active tab
        tabs = self.query_one("#tabs", TabbedContent)
        active = tabs.active
        try:
            if active == "overview":
                self.query_one("#overview-screen", OverviewScreen).update_metrics(metrics, history)
            elif active == "cpu":
                self.query_one("#cpu-screen", CPUDetailScreen).update_metrics(metrics, history)
            elif active == "memory":
                self.query_one("#memory-screen", MemoryDetailScreen).update_metrics(metrics, history)
            elif active == "disk":
                self.query_one("#disk-screen", DiskDetailScreen).update_metrics(metrics, history)
            elif active == "network":
                self.query_one("#network-screen", NetworkDetailScreen).update_metrics(metrics, history)
            elif active == "process":
                self.query_one("#process-screen", ProcessScreen).update_metrics(metrics, history)
            elif active == "systemd":
                self.query_one("#systemd-screen", SystemdScreen).update_metrics(metrics, history)
        except Exception:
            pass

    # --- Actions ---

    def action_tab(self, tab_id: str) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = tab_id
        self._active_tab = tab_id
        # Update hints based on tab
        hints = self.query_one("#hints", HintBar)
        if tab_id == "process":
            hints.set_hints(
                "[k]k[/k] Kill  [k]s[/k] Stop  [k]r[/k] Resume  [k]b[/k] Blacklist  [k]/[/k] Filter  [k]1-7[/k] Tabs"
            )
        elif tab_id == "systemd":
            hints.set_hints("[k]/[/k] Filter  [k]1-7[/k] Tabs  [k]p[/k] Profiles  [k]q[/k] Quit")
        else:
            hints.set_hints("[k]1-7[/k] Tabs  [k]p[/k] Profiles  [k]T[/k] Theme  [k]q[/k] Quit")

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

    def action_quit_app(self) -> None:
        self.collector_manager.stop()
        self.exit()

    def on_unmount(self) -> None:
        self.collector_manager.stop()
