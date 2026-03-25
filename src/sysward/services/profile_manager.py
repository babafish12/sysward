"""Performance profile manager — writes governor/turbo/EPP to sysfs."""

from __future__ import annotations

from pathlib import Path

from sysward.models.profile import PerformanceProfile
from sysward.services.privilege import write_sysfs, write_sysfs_privileged

_CPU_BASE = Path("/sys/devices/system/cpu")
_NO_TURBO = _CPU_BASE / "intel_pstate" / "no_turbo"


class ProfileManager:
    def __init__(self) -> None:
        self._active_profile: str | None = None

    @property
    def active_profile(self) -> str | None:
        return self._active_profile

    def detect_current(self) -> str | None:
        """Try to detect which profile matches current settings."""
        gov_file = _CPU_BASE / "cpu0" / "cpufreq" / "scaling_governor"
        if not gov_file.exists():
            return None
        try:
            gov = gov_file.read_text().strip()
        except (PermissionError, OSError):
            return None

        turbo = None
        if _NO_TURBO.exists():
            try:
                turbo = int(_NO_TURBO.read_text().strip()) == 0
            except (ValueError, PermissionError):
                pass

        epp = None
        epp_file = _CPU_BASE / "cpu0" / "cpufreq" / "energy_performance_preference"
        if epp_file.exists():
            try:
                epp = epp_file.read_text().strip()
            except (PermissionError, OSError):
                pass

        # Match against known profiles
        if gov == "performance" and turbo is True:
            self._active_profile = "max_performance"
        elif gov == "powersave" and turbo is False:
            self._active_profile = "powersave"
        elif gov == "powersave" and turbo is True:
            self._active_profile = "balanced"
        else:
            self._active_profile = None

        return self._active_profile

    def apply(self, profile: PerformanceProfile) -> tuple[bool, str]:
        """Apply a performance profile. Returns (success, message)."""
        errors: list[str] = []

        # Count CPUs
        cpu_count = 0
        while (_CPU_BASE / f"cpu{cpu_count}" / "cpufreq").exists():
            cpu_count += 1
        if cpu_count == 0:
            return False, "No CPUs with cpufreq found"

        # Set governor
        for i in range(cpu_count):
            gov_path = _CPU_BASE / f"cpu{i}" / "cpufreq" / "scaling_governor"
            if not write_sysfs(gov_path, profile.governor):
                if not write_sysfs_privileged(gov_path, profile.governor):
                    errors.append(f"Failed to set governor on cpu{i}")
                    break

        # Set turbo (intel_pstate: no_turbo is inverted)
        if _NO_TURBO.exists():
            turbo_val = "0" if profile.turbo else "1"
            if not write_sysfs(_NO_TURBO, turbo_val):
                if not write_sysfs_privileged(_NO_TURBO, turbo_val):
                    errors.append("Failed to set turbo")

        # Set EPP
        for i in range(cpu_count):
            epp_path = _CPU_BASE / f"cpu{i}" / "cpufreq" / "energy_performance_preference"
            if epp_path.exists():
                if not write_sysfs(epp_path, profile.epp):
                    if not write_sysfs_privileged(epp_path, profile.epp):
                        errors.append(f"Failed to set EPP on cpu{i}")
                        break

        if errors:
            return False, "; ".join(errors)

        self._active_profile = profile.name
        return True, f"Applied profile: {profile.display_name}"
