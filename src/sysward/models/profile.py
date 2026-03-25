"""Performance profile dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PerformanceProfile:
    name: str
    governor: str
    turbo: bool
    epp: str  # energy_performance_preference

    @classmethod
    def from_dict(cls, name: str, data: dict) -> PerformanceProfile:
        return cls(
            name=name,
            governor=data.get("governor", "powersave"),
            turbo=data.get("turbo", True),
            epp=data.get("epp", "balance_performance"),
        )

    @property
    def display_name(self) -> str:
        return self.name.replace("_", " ").title()
