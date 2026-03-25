# Sysward

A terminal-based system monitor and performance manager built for Arch Linux. Sysward gives you real-time insight into CPU, memory, GPU, battery, disk, network, processes, and systemd services — all from a single TUI with keyboard-driven navigation.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Textual](https://img.shields.io/badge/TUI-Textual-green)
![Arch Linux](https://img.shields.io/badge/Platform-Arch%20Linux-1793d1)

## What This Does

Sysward reads directly from `/proc` and `/sys` — no external monitoring daemons, no psutil dependency. It collects hardware metrics at two intervals (fast: 1s for CPU/RAM/GPU/sensors/network/battery, slow: 5s for disk/processes/systemd) and displays them across 7 tabbed screens with sparkline history, color-coded usage bars, and configurable alerts.

It also includes a **performance profile manager** that can switch between `max_performance`, `balanced`, and `powersave` modes by writing CPU governor, turbo boost, and energy performance preference settings directly to sysfs.

## Features

- **Overview Dashboard** — CPU, RAM, GPU, and battery cards with sparkline graphs, sensor readouts, network throughput, and disk I/O at a glance
- **CPU Detail** — per-core usage bars, frequency per core, governor, turbo boost state, EPP, temperature history
- **Memory Detail** — RAM/swap usage with buffer/cache breakdown, zram stats
- **Disk Detail** — per-device read/write throughput, mount point usage
- **Network Detail** — per-interface RX/TX rates, state indicators
- **Process Manager** — sortable/filterable process table with kill (SIGTERM), stop (SIGSTOP), resume (SIGCONT), and process blacklisting
- **Systemd Services** — filterable service list showing unit state and sub-state
- **Performance Profiles** — switch between predefined CPU governor/turbo/EPP profiles via a single keypress
- **Configurable Alerts** — warnings for high CPU temp, CPU usage, RAM usage, and low battery
- **Process Blacklist** — automatically stop or kill processes that match a configured list
- **6 Built-in Themes** — Tokyo Night, Catppuccin Mocha, Dracula, Nord, Gruvbox Dark, One Dark
- **TOML Config** — all settings stored in `~/.config/sysward/config.toml`

## Screenshots

> Run `sysward` in a terminal with at least 120x40 characters for best results.

## Getting Started

### Requirements

- Python 3.11+
- Arch Linux (reads from `/proc` and `/sys` — other Linux distros may work but are untested)

### Installation

```bash
git clone https://github.com/babafish12/sysward.git
cd sysward
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run

```bash
sysward
```

For performance profile switching (governor, turbo boost), run with elevated privileges:

```bash
sudo sysward
```

## Keybindings

| Key | Action |
|-----|--------|
| `1`-`7` | Switch tabs (Overview, CPU, Memory, Disk, Network, Processes, Services) |
| `p` | Open performance profile selector |
| `T` | Cycle through themes |
| `k` | Kill selected process (SIGTERM) |
| `s` | Stop selected process (SIGSTOP) |
| `r` | Resume selected process (SIGCONT) |
| `b` | Add selected process to blacklist |
| `/` | Toggle filter in process/service views |
| `q` | Quit |

## Configuration

Sysward stores its config at `~/.config/sysward/config.toml`. A default config is created on first run.

```toml
[general]
theme = "tokyo-night"
refresh_fast = 1.0    # seconds — CPU, RAM, GPU, sensors, network, battery
refresh_slow = 5.0    # seconds — disk, processes, systemd

[alerts]
enabled = true
cooldown = 60         # seconds between repeated alerts
cpu_temp_warn = 80
cpu_temp_crit = 95
cpu_usage_warn = 90
ram_usage_warn = 85
battery_low = 20
battery_critical = 10

[profiles.max_performance]
governor = "performance"
turbo = true
epp = "performance"

[profiles.balanced]
governor = "powersave"
turbo = true
epp = "balance_performance"

[profiles.powersave]
governor = "powersave"
turbo = false
epp = "power"

[blacklist]
# process_name = "stop" or "kill"
```

## How It Works

### Architecture

```
sysward/
├── app.py                 # Main Textual app — tab layout, keybindings, collection loops
├── theme.py               # 6 color themes
├── collectors/            # Hardware data collection (reads /proc and /sys)
│   ├── base.py            # Abstract BaseCollector
│   ├── cpu.py             # /proc/stat, sysfs freq/governor/turbo/EPP
│   ├── memory.py          # /proc/meminfo, zram stats
│   ├── gpu.py             # Intel integrated GPU via sysfs
│   ├── battery.py         # /sys/class/power_supply
│   ├── sensors.py         # hwmon temperature + fan RPM
│   ├── disk.py            # /proc/diskstats, /proc/mounts
│   ├── network.py         # /proc/net/dev, sysfs operstate
│   ├── process.py         # /proc/[pid]/stat + status + cmdline
│   └── systemd.py         # systemctl list-units via subprocess
├── models/
│   ├── config.py          # TOML config manager
│   ├── profile.py         # PerformanceProfile dataclass
│   ├── blacklist_entry.py # Blacklist entry model
│   └── history.py         # RingBuffer for sparkline data
├── services/
│   ├── collector_manager.py  # Orchestrates fast/slow collection cycles
│   ├── profile_manager.py    # Applies CPU governor/turbo/EPP to sysfs
│   ├── process_manager.py    # kill/stop/resume via os.kill + blacklist enforcement
│   ├── alert_manager.py      # Threshold-based alerts with cooldown
│   └── privilege.py          # Root privilege detection
├── widgets/
│   ├── metric_card.py     # Card with label, bar, sparkline
│   ├── usage_bar.py       # Color-coded usage bar (green/yellow/red)
│   ├── header_bar.py      # Hostname, CPU model, uptime, active profile
│   ├── hint_bar.py        # Dynamic keybinding hints
│   ├── process_table.py   # Sortable process DataTable
│   └── service_table.py   # Filterable systemd service DataTable
└── screens/
    ├── overview.py        # Dashboard with 4 metric cards + info lines
    ├── cpu_detail.py      # Per-core bars, freq table, sparkline history
    ├── memory_detail.py   # RAM/swap bars, cache/buffer breakdown
    ├── disk_detail.py     # Per-device I/O rates, mount usage
    ├── network_detail.py  # Per-interface rates
    ├── process_screen.py  # Process table with filter
    ├── systemd_screen.py  # Service table with filter
    ├── profile_screen.py  # Profile selector modal
    └── confirm_dialog.py  # Yes/No confirmation dialog
```

### Data Collection

All collectors inherit from `BaseCollector` and implement `is_available()` and `collect()`. The `CollectorManager` discovers which hardware is present at startup and then runs two background threads:

- **Fast loop** (default 1s): CPU, memory, GPU, battery, sensors, network
- **Slow loop** (default 5s): disk I/O, processes, systemd services

Only the active tab's UI is updated each cycle to minimize rendering overhead. Metric history is stored in fixed-size ring buffers for sparkline graphs.

## Tech Stack

- **TUI Framework**: [Textual](https://textual.textualize.io/) — modern Python TUI framework with CSS-like styling
- **Rich Text**: [Rich](https://rich.readthedocs.io/) — colored bars and formatted output
- **Config**: [tomli_w](https://github.com/hukkin/tomli-w) + stdlib `tomllib` — TOML read/write
- **Data Sources**: Direct reads from `/proc` and `/sys` — zero external dependencies for metrics

## License

MIT

## Changelog

### 2026-03-25
- Initial release with 7 monitoring tabs, performance profiles, process management, alerts, 6 themes, and TOML configuration
