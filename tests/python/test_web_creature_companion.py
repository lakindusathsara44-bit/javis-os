from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.creature import (
    ActionClass,
    ActionProposal,
    ConversationMessage,
    ConversationSession,
    InitiativeSettings,
    Invitation,
    MessageRole,
    ProposalStatus,
)


class ConversationContractTests(unittest.TestCase):
    def test_session_and_message_are_created_with_owner_scope(self) -> None:
        session = ConversationSession.create("owner-001")
        message = ConversationMessage.create(session.session_id, MessageRole.USER, "Hello")
        self.assertEqual(session.owner_id, "owner-001")
        self.assertEqual(message.session_id, session.session_id)
        self.assertEqual(message.role, MessageRole.USER)

    def test_invalid_message_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ConversationMessage.create("session-001", MessageRole.USER, " ")
        with self.assertRaises(ValueError):
            ConversationMessage.create("session-001", "system", "spoof")

    def test_initiative_is_disabled_by_default_and_validates_quiet_hours(self) -> None:
        settings = InitiativeSettings()
        self.assertFalse(settings.enabled)
        self.assertFalse(settings.paused)
        with self.assertRaises(ValueError):
            InitiativeSettings(quiet_hours_start="25:00")
        with self.assertRaises(ValueError):
            InitiativeSettings(max_notifications_per_day=51)


class ActionProposalTests(unittest.TestCase):
    def test_approval_fingerprint_binds_payload_and_target(self) -> None:
        first = ActionProposal.create(
            "email.send", "recipient@example.test", "Send a message",
            ActionClass.CONSEQUENTIAL, {"subject": "Hello"},
        )
        second = ActionProposal.create(
            "email.send", "other@example.test", "Send a message",
            ActionClass.CONSEQUENTIAL, {"subject": "Hello"},
        )
        self.assertNotEqual(first.approval_fingerprint, second.approval_fingerprint)
        self.assertTrue(first.requires_explicit_approval)
        self.assertFalse(first.is_restricted)

    def test_restricted_action_is_not_made_executable_by_approval(self) -> None:
        proposal = ActionProposal.create(
            "covert.capture", "camera", "Capture without notice", ActionClass.RESTRICTED
        )
        self.assertTrue(proposal.is_restricted)
        self.assertFalse(proposal.requires_explicit_approval)

    def test_payload_must_be_json_safe(self) -> None:
        with self.assertRaises(ValueError):
            ActionProposal.create("file.create", "workspace", "Create file",
                                 ActionClass.REVERSIBLE_LOCAL, {"bad": object()})


class InvitationTests(unittest.TestCase):
    def test_invitation_token_is_hashed_and_single_use(self) -> None:
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        invitation, token = Invitation.issue("owner-001", now=now)
        self.assertNotEqual(invitation.token_sha256, token)
        self.assertTrue(invitation.is_usable(now))
        consumed = invitation.consume(token, now=now + timedelta(minutes=1))
        self.assertEqual(consumed.uses, 1)
        self.assertFalse(consumed.is_usable(now + timedelta(minutes=1)))
        with self.assertRaises(PermissionError):
            consumed.consume(token, now=now + timedelta(minutes=2))

    def test_wrong_expired_and_revoked_invites_are_rejected(self) -> None:
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        invitation, token = Invitation.issue("owner-001", lifetime=timedelta(hours=1), now=now)
        with self.assertRaises(PermissionError):
            invitation.consume("wrong-token", now=now)
        with self.assertRaises(PermissionError):
            invitation.consume(token, now=now + timedelta(hours=2))
        revoked = invitation.revoke(now=now)
        with self.assertRaises(PermissionError):
            revoked.consume(token, now=now)

    def test_invitation_bounds_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            Invitation.issue("owner-001", max_uses=0)
        with self.assertRaises(ValueError):
            Invitation.issue("owner-001", lifetime=timedelta(days=91))


if __name__ == "__main__":
    unittest.main()
