from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.creature.accounts import AccountStore, PasswordHasher, normalize_email


class AccountStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "creature-auth.sqlite3"
        self.store = AccountStore(self.database)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def create_owner(self):
        return self.store.bootstrap_owner(
            "Owner@Example.test",
            "a-long-owner-password-123",
            bootstrap_enabled=True,
        )

    def test_owner_bootstrap_is_explicit_and_one_time(self) -> None:
        with self.assertRaises(PermissionError):
            self.store.bootstrap_owner(
                "owner@example.test", "a-long-owner-password-123"
            )
        owner = self.create_owner()
        self.assertEqual(owner.role, "owner")
        self.assertEqual(owner.email, "owner@example.test")
        with self.assertRaises(PermissionError):
            self.create_owner()

    def test_password_policy_and_hash_verification(self) -> None:
        salt, digest, iterations = PasswordHasher.hash_password("a-very-long-password")
        self.assertNotEqual(salt, digest)
        self.assertTrue(PasswordHasher.verify("a-very-long-password", salt, digest, iterations))
        self.assertFalse(PasswordHasher.verify("wrong-password", salt, digest, iterations))
        with self.assertRaises(ValueError):
            PasswordHasher.hash_password("short")

    def test_invitation_registration_is_single_use_and_token_is_not_stored(self) -> None:
        owner = self.create_owner()
        invite = self.store.issue_invitation(owner.account_id)
        self.assertNotEqual(stored, invite.token)
        with sqlite3.connect(self.database) as db:
            stored = db.execute(
                "SELECT token_sha256 FROM creature_invitations WHERE invitation_id=?",
                (invite.invitation_id,),
            ).fetchone()[0]
        import hashlib
        self.assertEqual(stored, hashlib.sha256(invite.token.encode()).hexdigest())
        member = self.store.accept_invitation(
            invite.token, "Member@Example.test", "a-long-member-password-123"
        )
        self.assertEqual(member.role, "member")
        self.assertEqual(member.email, "member@example.test")
        with self.assertRaises(PermissionError):
            self.store.accept_invitation(
                invite.token, "other@example.test", "a-long-other-password-123"
            )

    def test_invalid_and_revoked_invites_are_rejected(self) -> None:
        owner = self.create_owner()
        invite = self.store.issue_invitation(owner.account_id)
        with self.assertRaises(PermissionError):
            self.store.accept_invitation(
                "not-a-valid-invitation-token", "member@example.test",
                "a-long-member-password-123",
            )
        self.assertTrue(self.store.revoke_invitation(owner.account_id, invite.invitation_id))
        with self.assertRaises(PermissionError):
            self.store.accept_invitation(
                invite.token, "member@example.test", "a-long-member-password-123"
            )

    def test_duplicate_email_does_not_consume_invitation(self) -> None:
        owner = self.create_owner()
        invite_one = self.store.issue_invitation(owner.account_id)
        self.store.accept_invitation(
            invite_one.token, "member@example.test", "a-long-member-password-123"
        )
        invite_two = self.store.issue_invitation(owner.account_id)
        with self.assertRaises(ValueError):
            self.store.accept_invitation(
                invite_two.token, "MEMBER@example.test", "a-long-member-password-123"
            )
        account = self.store.accept_invitation(
            invite_two.token, "second@example.test", "a-long-second-password-123"
        )
        self.assertEqual(account.email, "second@example.test")

    def test_owner_only_invitation_management(self) -> None:
        owner = self.create_owner()
        invite = self.store.issue_invitation(owner.account_id)
        member = self.store.accept_invitation(
            invite.token, "member@example.test", "a-long-member-password-123"
        )
        with self.assertRaises(PermissionError):
            self.store.issue_invitation(member.account_id)
        with self.assertRaises(PermissionError):
            self.store.revoke_invitation(member.account_id, invite.invitation_id)

    def test_login_and_opaque_session_revocation(self) -> None:
        owner = self.create_owner()
        account = self.store.authenticate("OWNER@example.test", "a-long-owner-password-123")
        self.assertEqual(account.account_id, owner.account_id)
        with self.assertRaises(PermissionError):
            self.store.authenticate("owner@example.test", "incorrect-password")
        token, session = self.store.create_session(account.account_id)
        self.assertNotIn(token, session.session_id)
        resolved = self.store.resolve_session(token)
        self.assertEqual(resolved.account.account_id, account.account_id)
        self.assertTrue(self.store.revoke_session(token))
        with self.assertRaises(PermissionError):
            self.store.resolve_session(token)

    def test_owner_can_revoke_all_member_sessions(self) -> None:
        owner = self.create_owner()
        invite = self.store.issue_invitation(owner.account_id)
        member = self.store.accept_invitation(
            invite.token, "member@example.test", "a-long-member-password-123"
        )
        token, _ = self.store.create_session(member.account_id)
        self.assertEqual(self.store.revoke_all_sessions(owner.account_id, member.account_id), 1)
        with self.assertRaises(PermissionError):
            self.store.resolve_session(token)

    def test_session_lifetime_is_bounded(self) -> None:
        with self.assertRaises(ValueError):
            AccountStore(self.database, session_lifetime=timedelta(days=31))

    def test_email_normalization(self) -> None:
        self.assertEqual(normalize_email("  USER@Example.test "), "user@example.test")
        with self.assertRaises(ValueError):
            normalize_email("not-an-email")


if __name__ == "__main__":
    unittest.main()
