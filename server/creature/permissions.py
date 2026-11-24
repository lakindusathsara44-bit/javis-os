"""Host-owned, deny-by-default capability policy."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CapabilityPolicy:
    """An immutable snapshot of explicitly granted capabilities.

    This policy is not a substitute for host authentication or resource-level
    authorization. The host must construct it from trusted configuration.
    """

    grants: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.grants, frozenset):
            raise TypeError("grants must be a frozenset")
        if any(not isinstance(item, str) or not item.strip() for item in self.grants):
            raise ValueError("capability names must be non-empty strings")

    def allows(self, capability: str) -> bool:
        return isinstance(capability, str) and capability in self.grants

    def require(self, capability: str) -> None:
        if not self.allows(capability):
            raise PermissionError(f"capability not granted: {capability}")
