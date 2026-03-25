"""Blacklist entry dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BlacklistEntry:
    name: str
    action: str  # "stop" or "kill"

    @classmethod
    def from_config(cls, blacklist: dict[str, str]) -> list[BlacklistEntry]:
        return [cls(name=k, action=v) for k, v in blacklist.items()]
