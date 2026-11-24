"""Read-only, privacy-minimized WEB CREATURE dashboard snapshot."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .identity import CreatureIdentity
from .models import CreatureState, GoalStatus


@dataclass(frozen=True, slots=True)
class DashboardSnapshot:
    """A bounded status view; never includes memory or research content."""

    creature_id: str
    name: str
    platform: str
    schema_version: int
    state: str
    captured_at: str
    event_count: int
    memory_count: int
    research_count: int
    review_count: int
    goal_counts: tuple[tuple[str, int], ...]
    latest_event_type: str | None
    latest_event_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "creature_id": self.creature_id,
            "name": self.name,
            "platform": self.platform,
            "schema_version": self.schema_version,
            "state": self.state,
            "captured_at": self.captured_at,
            "counts": {
                "events": self.event_count,
                "memories": self.memory_count,
                "research_reports": self.research_count,
                "knowledge_reviews": self.review_count,
                "goals": dict(self.goal_counts),
            },
            "latest_event": (
                {"event_type": self.latest_event_type, "created_at": self.latest_event_at}
                if self.latest_event_type is not None else None
            ),
        }


def build_dashboard_snapshot(
    identity: CreatureIdentity,
    state: CreatureState,
    summary: dict[str, Any],
) -> DashboardSnapshot:
    """Build a JSON-safe snapshot from trusted local metadata only."""
    if not isinstance(identity, CreatureIdentity):
        raise TypeError("identity must be a CreatureIdentity")
    if not isinstance(state, CreatureState):
        raise TypeError("state must be a CreatureState")
    if not isinstance(summary, dict):
        raise TypeError("summary must be a dictionary")

    def count(name: str) -> int:
        value = summary.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
        return value

    raw_goals = summary.get("goal_counts")
    if not isinstance(raw_goals, dict):
        raise ValueError("goal_counts must be a dictionary")
    goals: list[tuple[str, int]] = []
    for status in GoalStatus:
        value = raw_goals.get(status.value, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"goal count for {status.value} must be a non-negative integer")
        goals.append((status.value, value))

    latest_type = summary.get("latest_event_type")
    latest_at = summary.get("latest_event_at")
    if latest_type is not None and (not isinstance(latest_type, str) or not latest_type or len(latest_type) > 100):
        raise ValueError("latest_event_type must be a non-empty string or None")
    if latest_at is not None and (not isinstance(latest_at, str) or len(latest_at) > 40):
        raise ValueError("latest_event_at must be a timestamp string or None")
    if (latest_type is None) != (latest_at is None):
        raise ValueError("latest event type and timestamp must both be present or both be None")

    return DashboardSnapshot(
        creature_id=identity.creature_id,
        name=identity.name,
        platform=identity.platform,
        schema_version=identity.schema_version,
        state=state.value,
        captured_at=datetime.now(timezone.utc).isoformat(),
        event_count=count("event_count"),
        memory_count=count("memory_count"),
        research_count=count("research_count"),
        review_count=count("review_count"),
        goal_counts=tuple(goals),
        latest_event_type=latest_type,
        latest_event_at=latest_at,
    )
