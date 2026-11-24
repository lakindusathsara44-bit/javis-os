from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from server.creature import (
    CapabilityPolicy, CreatureIdentity, CreatureLifecycle, CreatureService,
    CreatureState, CreatureStore,
)
from server.creature.models import CreatureGoal, CreatureMemory, GoalStatus


def make_service(directory: str, grants: frozenset[str] | None = None) -> CreatureService:
    service = CreatureService(
        CreatureIdentity("web-creature-001"),
        CreatureStore(Path(directory) / "creature.sqlite3"),
        CapabilityPolicy(grants or frozenset()),
    )
    service.initialize()
    return service


class CreatureIdentityTests(unittest.TestCase):
    def test_valid_identity(self) -> None:
        identity = CreatureIdentity("web-creature-001")
        self.assertEqual(identity.name, "WEB CREATURE")
        self.assertEqual(identity.platform, "APOLONIA ALPHA")

    def test_invalid_identity_rejected(self) -> None:
        for value in ("", "../bad", "UPPERCASE", "ab", "has spaces"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CreatureIdentity(value)


class CreatureLifecycleTests(unittest.TestCase):
    def test_valid_lifecycle(self) -> None:
        lifecycle = CreatureLifecycle()
        self.assertEqual(lifecycle.state, CreatureState.DORMANT)
        lifecycle.start()
        lifecycle.pause()
        lifecycle.resume()
        lifecycle.stop()
        self.assertEqual(lifecycle.state, CreatureState.STOPPED)

    def test_invalid_transition_rejected(self) -> None:
        lifecycle = CreatureLifecycle()
        with self.assertRaises(ValueError):
            lifecycle.resume()
        lifecycle.stop()
        with self.assertRaises(ValueError):
            lifecycle.start()


class CreaturePermissionTests(unittest.TestCase):
    def test_default_policy_denies_everything(self) -> None:
        policy = CapabilityPolicy()
        self.assertFalse(policy.allows("memory.read"))
        with self.assertRaises(PermissionError):
            policy.require("memory.read")


class CreaturePersistenceTests(unittest.TestCase):
    def test_memory_provenance_hash_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = make_service(directory, frozenset({"memory.read", "memory.write"}))
            memory = CreatureMemory.create(
                "semantic", "Hybrid local and internet architecture", "approved-design",
                0.9, source_kind="owner_input", verification_status="verified", tags=["architecture"],
            )
            memory_id = service.remember(memory)
            self.assertGreater(memory_id, 0)
            found = service.read_memory(query="internet", verification_status="verified")
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["content_hash"], memory.content_hash)
            self.assertEqual(found[0]["tags"], ["architecture"])
            self.assertEqual(found[0]["source"], "approved-design")

    def test_unverified_memory_is_not_silently_marked_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = make_service(directory, frozenset({"memory.read", "memory.write"}))
            service.remember(CreatureMemory.create("semantic", "Claim from web", "https://example.test"))
            self.assertEqual(service.read_memory(verification_status="unverified")[0]["verification_status"], "unverified")
            self.assertEqual(service.read_memory(verification_status="verified"), [])

    def test_memory_write_requires_explicit_capability(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = make_service(directory)
            with self.assertRaises(PermissionError):
                service.remember(CreatureMemory.create("episodic", "A test event.", "unit-test"))


class CreatureGoalTests(unittest.TestCase):
    def test_goal_create_list_and_transitions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = make_service(directory, frozenset({"goal.read", "goal.write"}))
            goal_id = service.create_goal(CreatureGoal.create(
                "Build verified memory retrieval", "Implement searchable memory",
                "Tests prove retrieval and access control", priority=1,
            ))
            self.assertGreater(goal_id, 0)
            active = service.transition_goal(goal_id, GoalStatus.ACTIVE)
            self.assertEqual(active["status"], "active")
            paused = service.transition_goal(goal_id, GoalStatus.PAUSED)
            self.assertEqual(paused["status"], "paused")
            resumed = service.transition_goal(goal_id, GoalStatus.ACTIVE)
            self.assertEqual(resumed["status"], "active")
            completed = service.transition_goal(goal_id, GoalStatus.COMPLETED)
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(service.list_goals(status="completed")[0]["id"], goal_id)

    def test_terminal_goal_cannot_be_reopened(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = make_service(directory, frozenset({"goal.read", "goal.write"}))
            goal_id = service.create_goal(CreatureGoal.create("One-time task"))
            service.transition_goal(goal_id, GoalStatus.CANCELLED)
            with self.assertRaises(ValueError):
                service.transition_goal(goal_id, GoalStatus.ACTIVE)

    def test_goal_operations_require_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = make_service(directory)
            with self.assertRaises(PermissionError):
                service.create_goal(CreatureGoal.create("Blocked"))
            with self.assertRaises(PermissionError):
                service.list_goals()


if __name__ == "__main__":
    unittest.main()
