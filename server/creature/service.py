"""Explicit WEB CREATURE service facade with capability-gated memory and goals."""
from __future__ import annotations

from .identity import CreatureIdentity
from .lifecycle import CreatureLifecycle
from .models import CreatureEvent, CreatureGoal, CreatureMemory, CreatureState, GoalStatus
from .permissions import CapabilityPolicy
from .store import CreatureStore
from .verification import EvidenceFinding, KnowledgeReview, ResearchVerifier, ReviewDecision
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
        self.verifier = ResearchVerifier()

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

    def _load_research_report(self, research_id: int) -> ResearchReport:
        saved = self.store.get_research_report(research_id)
        if saved is None:
            raise KeyError(f"research report not found: {research_id}")
        from .research import SourceEvidence
        raw = saved["report"]
        return ResearchReport(
            question=raw["question"],
            sources=tuple(SourceEvidence(**item) for item in raw["sources"]),
            shared_statements=tuple(raw["shared_statements"]),
            unique_statements=tuple((domain, tuple(items)) for domain, items in raw["unique_statements"]),
            generated_at=raw["generated_at"],
        )

    def research_and_store(self, plan: ResearchPlan) -> tuple[int, ResearchReport]:
        """Run a bounded research plan and persist its unverified evidence report."""
        self.policy.require("research.persist")
        report = self.research(plan)
        research_id = self.store.save_research_report(report)
        self._audit(
            "research.persisted", research_id=research_id,
            question=report.question, source_count=len(report.sources),
        )
        return research_id, report

    def research_goal(self, goal_id: int, plan: ResearchPlan) -> tuple[int, ResearchReport]:
        """Execute one explicitly requested research action for an already-active goal."""
        self.policy.require("goal.execute")
        if self.status != CreatureState.ACTIVE:
            raise RuntimeError("creature must be active to execute a goal")
        goal = self.store.get_goal(goal_id)
        if goal is None:
            raise KeyError(f"goal not found: {goal_id}")
        if goal["status"] != GoalStatus.ACTIVE.value:
            raise RuntimeError("goal must be active before research execution")
        research_id, report = self.research_and_store(plan)
        self._audit("goal.research.completed", goal_id=goal_id, research_id=research_id)
        return research_id, report

    def evaluate_research(self, research_id: int) -> tuple[EvidenceFinding, ...]:
        self.policy.require("research.read")
        report = self._load_research_report(research_id)
        return self.verifier.evaluate(report)

    def review_knowledge_claim(
        self,
        research_id: int,
        finding_id: str,
        decision: ReviewDecision,
        *,
        reviewer: str,
        rationale: str,
    ) -> int:
        """Record an explicit reviewer decision; no source can self-verify."""
        self.policy.require("knowledge.verify")
        if self.status != CreatureState.ACTIVE:
            raise RuntimeError("creature must be active to review knowledge")
        findings = self.verifier.evaluate(self._load_research_report(research_id))
        finding = next((item for item in findings if item.finding_id == finding_id), None)
        if finding is None:
            raise KeyError(f"finding not found in research report: {finding_id}")
        review = self.verifier.review(
            finding, decision, reviewer=reviewer, rationale=rationale,
        )
        review_id = self.store.save_knowledge_review(research_id, review)
        self._audit(
            "knowledge.reviewed", research_id=research_id, finding_id=finding_id,
            decision=decision.value, reviewer=review.reviewer,
        )
        return review_id

    def promote_verified_claim_to_memory(self, research_id: int, finding_id: str) -> int:
        """Promote only after a separate explicit verification and promotion grant."""
        self.policy.require("knowledge.promote")
        self.policy.require("memory.write")
        if self.status != CreatureState.ACTIVE:
            raise RuntimeError("creature must be active to promote knowledge")
        reviews = self.store.list_knowledge_reviews(research_id)
        latest_review = next(
            (item for item in reversed(reviews) if item["finding_id"] == finding_id),
            None,
        )
        if latest_review is None or latest_review["decision"] != ReviewDecision.VERIFIED.value:
            raise PermissionError("finding has no current explicit verified review")
        finding = next(
            (item for item in self.verifier.evaluate(self._load_research_report(research_id))
             if item.finding_id == finding_id),
            None,
        )
        if finding is None:
            raise KeyError(f"finding not found in research report: {finding_id}")
        confidence = 0.8 if finding.evidence_level.value == "corroborated" else 0.6
        memory = CreatureMemory.create(
            "semantic", finding.statement,
            source=f"research:{research_id}#finding:{finding_id}",
            confidence=confidence, source_kind="web", verification_status="verified",
            tags=("research", "reviewed"),
        )
        memory_id = self.remember(memory)
        self._audit(
            "knowledge.promoted", research_id=research_id,
            finding_id=finding_id, memory_id=memory_id,
        )
        return memory_id

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
