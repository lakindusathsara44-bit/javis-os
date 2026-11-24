"""Explicit WEB CREATURE service facade with capability-gated memory and goals."""
from __future__ import annotations

from .identity import CreatureIdentity
from .lifecycle import CreatureLifecycle
from .models import CreatureEvent, CreatureGoal, CreatureMemory, CreatureState, GoalStatus
from .permissions import CapabilityPolicy
from .store import CreatureStore
from .observation import LocalFileObserver, LocalObservation
from .research import ResearchEngine, ResearchPlan, ResearchReport


class CreatureService:
    """Coordinates domain operations; the trusted host owns policy construction."""

    def __init__(
        self,
        identity: CreatureIdentity,
        store: CreatureStore,
        policy: CapabilityPolicy | None = None,
        *,
        local_observer: LocalFileObserver | None = None,
        research_engine: ResearchEngine | None = None,
    ) -> None:
        if not isinstance(identity, CreatureIdentity):
            raise TypeError("identity must be a CreatureIdentity")
        if not isinstance(store, CreatureStore):
            raise TypeError("store must be a CreatureStore")
        self.identity = identity
        self.store = store
        self.policy = policy if policy is not None else CapabilityPolicy()
        if not isinstance(self.policy, CapabilityPolicy):
            raise TypeError("policy must be a CapabilityPolicy")
        if local_observer is not None and not isinstance(local_observer, LocalFileObserver):
            raise TypeError("local_observer must be a LocalFileObserver or None")
        if research_engine is not None and not isinstance(research_engine, ResearchEngine):
            raise TypeError("research_engine must be a ResearchEngine or None")
        self.local_observer = local_observer
        self.research_engine = research_engine
        self.lifecycle = CreatureLifecycle()

    @property
    def status(self) -> CreatureState:
        return self.lifecycle.state

    def _audit(self, event_type: str, **payload: object) -> None:
        self.store.append_event(CreatureEvent.create(
            event_type, {"creature_id": self.identity.creature_id, **payload}
        ))

    def initialize(self) -> None:
        self.store.initialize()
        self.lifecycle.transition(CreatureState.INITIALIZING)
        try:
            self._audit("creature.initialized", schema_version=self.identity.schema_version)
        except Exception:
            self.lifecycle.fail()
            raise
        self.lifecycle.transition(CreatureState.ACTIVE)

    def pause(self) -> None:
        self.lifecycle.pause()
        self._audit("creature.paused")

    def resume(self) -> None:
        self.lifecycle.resume()
        self._audit("creature.resumed")

    def stop(self) -> None:
        self.lifecycle.stop()
        self._audit("creature.stopped")

    def remember(self, memory: CreatureMemory) -> int:
        self.policy.require("memory.write")
        if self.status != CreatureState.ACTIVE:
            raise RuntimeError("creature must be active to write memory")
        memory_id = self.store.save_memory(memory)
        self._audit(
            "memory.created", memory_id=memory_id, memory_type=memory.memory_type,
            verification_status=memory.verification_status, content_hash=memory.content_hash,
        )
        return memory_id

    def read_memory(
        self,
        memory_type: str | None = None,
        limit: int = 100,
        query: str | None = None,
        verification_status: str | None = None,
    ) -> list[dict]:
        self.policy.require("memory.read")
        return self.store.list_memory(
            memory_type=memory_type, limit=limit, query=query,
            verification_status=verification_status,
        )

    def create_goal(self, goal: CreatureGoal) -> int:
        self.policy.require("goal.write")
        if self.status != CreatureState.ACTIVE:
            raise RuntimeError("creature must be active to create goals")
        goal_id = self.store.create_goal(goal)
        self._audit("goal.created", goal_id=goal_id, priority=goal.priority, status=goal.status.value)
        return goal_id

    def list_goals(self, status: str | None = None, limit: int = 100) -> list[dict]:
        self.policy.require("goal.read")
        return self.store.list_goals(status=status, limit=limit)

    def transition_goal(self, goal_id: int, target: GoalStatus) -> dict:
        self.policy.require("goal.write")
        if self.status != CreatureState.ACTIVE:
            raise RuntimeError("creature must be active to change goals")
        updated = self.store.transition_goal(goal_id, target)
        self._audit("goal.transitioned", goal_id=goal_id, status=updated["status"])
        return updated

    def observe_local_file(self, path: str) -> LocalObservation:
        self.policy.require("local.read")
        if self.status != CreatureState.ACTIVE:
            raise RuntimeError("creature must be active to observe local files")
        if self.local_observer is None:
            raise RuntimeError("no host-approved local observer is configured")
        observation = self.local_observer.read_text(path)
        self._audit(
            "observation.local_file", relative_path=observation.relative_path,
            content_hash=observation.content_hash, size_bytes=observation.size_bytes,
        )
        return observation

    def research(self, plan: ResearchPlan) -> ResearchReport:
        self.policy.require("web.read")
        if self.status != CreatureState.ACTIVE:
            raise RuntimeError("creature must be active to research web sources")
        if self.research_engine is None:
            raise RuntimeError("no host-approved research transport is configured")
        report = self.research_engine.run(plan)
        self._audit(
            "research.completed",
            question=report.question,
            source_count=len(report.sources),
            source_hashes=[source.content_hash for source in report.sources],
            domains=[source.domain for source in report.sources],
        )
        return report
