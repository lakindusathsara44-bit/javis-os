"""Stable identity model for a WEB CREATURE instance."""
from __future__ import annotations

from dataclasses import dataclass
import re

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,63}$")


@dataclass(frozen=True, slots=True)
class CreatureIdentity:
    creature_id: str
    name: str = "WEB CREATURE"
    platform: str = "APOLONIA ALPHA"
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.creature_id, str) or not _ID_PATTERN.fullmatch(self.creature_id):
            raise ValueError("creature_id must be 3-64 lowercase letters, digits or hyphens and start with a letter")
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 100:
            raise ValueError("name must be a non-empty string of at most 100 characters")
        if not isinstance(self.platform, str) or not self.platform.strip() or len(self.platform) > 100:
            raise ValueError("platform must be a non-empty string of at most 100 characters")
        if isinstance(self.schema_version, bool) or not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise ValueError("schema_version must be a positive integer")
