"""TOML-based configuration manager."""

from __future__ import annotations

import tomllib
from pathlib import Path

import tomli_w

CONFIG_DIR = Path.home() / ".config" / "sysward"
CONFIG_FILE = CONFIG_DIR / "config.toml"


def _default_config() -> dict:
    return {
        "general": {
            "theme": "tokyo-night",
            "refresh_fast": 1.0,
            "refresh_slow": 5.0,
        },
        "alerts": {
            "enabled": True,
            "cooldown": 60,
            "cpu_temp_warn": 80,
            "cpu_temp_crit": 95,
            "cpu_usage_warn": 90,
            "ram_usage_warn": 85,
            "battery_low": 20,
            "battery_critical": 10,
            "fan_failure_enabled": True,
            "temp_rise_rate_warn": 10,
        },
        "cleaner": {
            "pacman_keep_versions": 2,
            "journal_max_size": "100M",
            "tmp_max_age_days": 7,
        },
        "export": {
            "default_format": "csv",
            "default_dir": "~/Documents",
        },
        "logging": {
            "session_logging": False,
            "max_log_size_mb": 5,
            "log_dir": "~/.local/share/sysward/logs",
            "session_log_interval": 5.0,
        },
        "fan_control": {
            "enabled": False,
            "default_level": "auto",
            "safety_temp_limit": 90,
        },
        "blacklist": {},
        "profiles": {
            "max_performance": {
                "governor": "performance",
                "turbo": True,
                "epp": "performance",
            },
            "balanced": {
                "governor": "powersave",
                "turbo": True,
                "epp": "balance_performance",
            },
            "powersave": {
                "governor": "powersave",
                "turbo": False,
                "epp": "power",
            },
        },
    }


class ConfigManager:
    def __init__(self, path: Path = CONFIG_FILE) -> None:
        self.path = path
        self._data: dict = _default_config()

    def load(self) -> None:
        if self.path.exists():
            with open(self.path, "rb") as f:
                saved = tomllib.load(f)
            # Merge with defaults so new keys are always present
            defaults = _default_config()
            for section, values in defaults.items():
                if section not in saved:
                    saved[section] = values
                elif isinstance(values, dict):
                    for k, v in values.items():
                        saved[section].setdefault(k, v)
            self._data = saved
        else:
            self._data = _default_config()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "wb") as f:
            tomli_w.dump(self._data, f)

    # --- General ---

    @property
    def theme(self) -> str:
        return self._data.get("general", {}).get("theme", "tokyo-night")

    @theme.setter
    def theme(self, value: str) -> None:
        self._data.setdefault("general", {})["theme"] = value

    @property
    def refresh_fast(self) -> float:
        return self._data.get("general", {}).get("refresh_fast", 1.0)

    @property
    def refresh_slow(self) -> float:
        return self._data.get("general", {}).get("refresh_slow", 5.0)

    # --- Alerts ---

    @property
    def alerts(self) -> dict:
        return self._data.get("alerts", {})

    # --- Cleaner ---

    @property
    def cleaner(self) -> dict:
        return self._data.get("cleaner", {})

    # --- Blacklist ---

    @property
    def blacklist(self) -> dict[str, str]:
        return self._data.get("blacklist", {})

    def add_to_blacklist(self, name: str, action: str) -> None:
        self._data.setdefault("blacklist", {})[name] = action
        self.save()

    def remove_from_blacklist(self, name: str) -> None:
        self._data.get("blacklist", {}).pop(name, None)
        self.save()

    # --- Profiles ---

    @property
    def profiles(self) -> dict[str, dict]:
        return self._data.get("profiles", {})

    def get_profile(self, name: str) -> dict | None:
        return self.profiles.get(name)

    # --- Export ---

    @property
    def export_format(self) -> str:
        return self._data.get("export", {}).get("default_format", "csv")

    @property
    def export_dir(self) -> str:
        return self._data.get("export", {}).get("default_dir", "~/Documents")

    # --- Fan Control ---

    @property
    def fan_control_enabled(self) -> bool:
        return self._data.get("fan_control", {}).get("enabled", False)

    @property
    def fan_control_config(self) -> dict:
        return self._data.get("fan_control", {})

    # --- Logging ---

    @property
    def session_logging_enabled(self) -> bool:
        return self._data.get("logging", {}).get("session_logging", False)

    @property
    def logging_config(self) -> dict:
        return self._data.get("logging", {})
