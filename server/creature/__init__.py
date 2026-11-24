"""WEB CREATURE subsystem for APOLONIA ALPHA.

Importing this package is intentionally side-effect free. The host application
must explicitly construct and start a CreatureService.
"""
from .identity import CreatureIdentity
from .lifecycle import CreatureLifecycle, CreatureState
from .permissions import CapabilityPolicy
from .service import CreatureService
from .store import CreatureStore

__all__ = [
    "CapabilityPolicy",
    "CreatureIdentity",
    "CreatureLifecycle",
    "CreatureService",
    "CreatureState",
    "CreatureStore",
]
