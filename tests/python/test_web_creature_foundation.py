from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.creature import (
    CapabilityPolicy,
    CreatureIdentity,
    CreatureLifecycle,
    CreatureService,
    CreatureState,
    CreatureStore,
)
from server.creature.models import CreatureMemory


class CreatureIdentityTests(unittest.TestCase):
    def test_valid_identity(self) -> None:
        identity = CreatureIdentity("web-creature-001")
        self.assertEqual(identity.name, "WEB CREATURE")
        self.assertEqual(identity.platform, "INDEPENDENT WEB CREATURE")

    def test_invalid_identity_rejected(self) -> None:
        for value in ("", "../bad", "UPPERCASE", "ab", "has spaces"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CreatureIdentity(value)


class CreatureLifecycleTests(unittest.TestCase):
    def test_valid_lifecycle(self) -> None:
        lifecycle = CreatureLifecycle()
        self.assertEqual(lifecycle.state, CreatureState.DORMANT)
        lifecycle.start()
        self.assertEqual(lifecycle.state, CreatureState.ACTIVE)
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
    def test_events_and_memory_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CreatureStore(Path(directory) / "creature.sqlite3")
            service = CreatureService(
                CreatureIdentity("web-creature-001"),
                store,
                CapabilityPolicy(frozenset({"memory.read", "memory.write"})),
            )
            service.initialize()
            memory = CreatureMemory.create(
                "semantic", "The project uses a hybrid environment.", "owner-approved-spec", 0.95
            )
            memory_id = service.remember(memory)
            self.assertGreater(memory_id, 0)
            records = service.read_memory("semantic")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["content"], memory.content)
            event_types = {event["event_type"] for event in store.list_events()}
            self.assertIn("creature.initialized", event_types)
            self.assertIn("memory.created", event_types)

    def test_memory_write_requires_explicit_capability(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = CreatureService(
                CreatureIdentity("web-creature-001"),
                CreatureStore(Path(directory) / "creature.sqlite3"),
            )
            service.initialize()
            memory = CreatureMemory.create("episodic", "A test event.", "unit-test")
            with self.assertRaises(PermissionError):
                service.remember(memory)


if __name__ == "__main__":
    unittest.main()
