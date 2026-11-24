"""Explicit WEB CREATURE service facade."""
from __future__ import annotations

from .identity import CreatureIdentity
from .lifecycle import CreatureLifecycle
from .models import CreatureEvent, CreatureMemory, CreatureState
from .permissions import CapabilityPolicy
from .store import CreatureStore


class CreatureService:
    """Coordinates identity, lifecycle, persistence and capability checks.

    Construction has no side effects. Call initialize() explicitly from a
    trusted host lifecycle after configuration and authorization are ready.
    """

    def __init__(
        self,
        identity: CreatureIdentity,
        store: CreatureStore,
        policy: CapabilityPolicy | None = None,
    ) -> None:
        self.identity = identity
        self.store = store
        self.policy = policy or CapabilityPolicy()
        self.lifecycle = CreatureLifecycle()

    @property
    def status(self) -> CreatureState:
        return self.lifecycle.state

    def initialize(self) -> None:
        self.store.initialize()
        self.lifecycle.transition(CreatureState.INITIALIZING)
        self.store.append_event(CreatureEvent.create(
            "creature.initialized",
            {"creature_id": self.identity.creature_id, "schema_version": self.identity.schema_version},
        ))
        self.lifecycle.transition(CreatureState.ACTIVE)

    def pause(self) -> None:
        self.lifecycle.pause()
        self.store.append_event(CreatureEvent.create("creature.paused", {"creature_id": self.identity.creature_id}))

    def resume(self) -> None:
        self.lifecycle.resume()
        self.store.append_event(CreatureEvent.create("creature.resumed", {"creature_id": self.identity.creature_id}))

    def stop(self) -> None:
        self.lifecycle.stop()
        self.store.append_event(CreatureEvent.create("creature.stopped", {"creature_id": self.identity.creature_id}))

    def remember(self, memory: CreatureMemory) -> int:
        self.policy.require("memory.write")
        if self.status != CreatureState.ACTIVE:
            raise RuntimeError("creature must be active to write memory")
        memory_id = self.store.save_memory(memory)
        self.store.append_event(CreatureEvent.create(
            "memory.created",
            {"creature_id": self.identity.creature_id, "memory_id": memory_id, "memory_type": memory.memory_type},
        ))
        return memory_id

    def read_memory(self, memory_type: str | None = None, limit: int = 100) -> list[dict]:
        self.policy.require("memory.read")
        return self.store.list_memory(memory_type=memory_type, limit=limit)
