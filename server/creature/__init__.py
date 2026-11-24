"""WEB CREATURE subsystem for APOLONIA ALPHA.

Importing this package is intentionally side-effect free. The trusted host
must explicitly construct and initialize a CreatureService.
"""
from .identity import CreatureIdentity
from .lifecycle import CreatureLifecycle, CreatureState
from .models import CreatureGoal, CreatureMemory, GoalStatus
from .permissions import CapabilityPolicy
from .service import CreatureService
from .store import CreatureStore

__all__ = [
    "CapabilityPolicy",
    "CreatureGoal",
    "CreatureIdentity",
    "CreatureLifecycle",
    "CreatureMemory",
    "CreatureService",
    "CreatureState",
    "CreatureStore",
    "GoalStatus",
]
