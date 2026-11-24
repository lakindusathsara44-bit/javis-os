from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.creature import (
    CapabilityPolicy,
    CreatureGoal,
    CreatureIdentity,
    CreatureMemory,
    CreatureService,
    CreatureStore,
    GoalStatus,
)


class DashboardSnapshotTests(unittest.TestCase):
    def make_service(self, directory: str, grants: frozenset[str]) -> CreatureService:
        service = CreatureService(
            CreatureIdentity("web-creature-001", name="WEB CREATURE"),
            CreatureStore(Path(directory) / "creature.sqlite3"),
            CapabilityPolicy(grants),
        )
        service.initialize()
        return service

    def test_dashboard_read_is_denied_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = self.make_service(directory, frozenset())
            with self.assertRaises(PermissionError):
                service.dashboard_snapshot()

    def test_snapshot_contains_aggregates_but_no_private_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = self.make_service(
                directory,
                frozenset({"dashboard.read", "goal.write", "memory.write"}),
            )
            goal_id = service.create_goal(CreatureGoal.create("Review approved docs", priority=2))
            service.transition_goal(goal_id, GoalStatus.ACTIVE)
            service.remember(CreatureMemory.create(
                "episodic", "private-memory-content-must-not-leak", "owner:test",
            ))
            service.pause()

            snapshot = service.dashboard_snapshot()
            data = snapshot.to_dict()

            self.assertEqual(data["state"], "paused")
            self.assertEqual(data["creature_id"], "web-creature-001")
            self.assertEqual(data["counts"]["memories"], 1)
            self.assertEqual(data["counts"]["goals"]["active"], 1)
            self.assertGreaterEqual(data["counts"]["events"], 4)
            self.assertEqual(data["latest_event"]["event_type"], "creature.paused")
            self.assertNotIn("private-memory-content-must-not-leak", repr(data))
            self.assertNotIn("payload", data["latest_event"])

    def test_empty_database_has_zero_counts_and_no_latest_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = CreatureService(
                CreatureIdentity("web-creature-001"),
                CreatureStore(Path(directory) / "creature.sqlite3"),
                CapabilityPolicy(frozenset({"dashboard.read"})),
            )
            service.store.initialize()
            snapshot = service.dashboard_snapshot().to_dict()
            self.assertEqual(snapshot["counts"]["events"], 0)
            self.assertEqual(snapshot["counts"]["memories"], 0)
            self.assertEqual(snapshot["counts"]["research_reports"], 0)
            self.assertIsNone(snapshot["latest_event"])


if __name__ == "__main__":
    unittest.main()
