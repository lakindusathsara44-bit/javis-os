from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.creature.account_store import AccountStore


class AccountStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = AccountStore(Path(self.temp.name) / "accounts.sqlite3")
        self.store.initialize()
        self.owner = self.store.bootstrap_owner(
            "Owner@Example.com", "a-very-long-owner-password", "Owner"
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_bootstrap_is_one_time(self) -> None:
        with self.assertRaises(PermissionError):
            self.store.bootstrap_owner(
                "other@example.com", "another-long-password", "Second"
            )

    def test_invitation_registration_and_single_use(self) -> None:
        invite = self.store.issue_invitation(self.owner.user_id)
        member = self.store.register_with_invitation(
            "Member@example.com", "a-very-long-member-password", "Member", invite.token
        )
        self.assertEqual(member.role, "member")
        self.assertEqual(member.email, "member@example.com")
        with self.assertRaises(PermissionError):
            self.store.register_with_invitation(
                "second@example.com", "a-very-long-member-password", "Second", invite.token
            )

    def test_member_cannot_issue_or_revoke_invitations(self) -> None:
        invite = self.store.issue_invitation(self.owner.user_id)
        member = self.store.register_with_invitation(
            "member@example.com", "a-very-long-member-password", "Member", invite.token
        )
        with self.assertRaises(PermissionError):
            self.store.issue_invitation(member.user_id)
        with self.assertRaises(PermissionError):
            self.store.revoke_invitation(member.user_id, "unknown")

    def test_expired_and_revoked_invitations_are_rejected(self) -> None:
        expired = self.store.issue_invitation(
            self.owner.user_id, lifetime=timedelta(seconds=1)
        )
        # Move the stored expiry into the past to avoid a timing-dependent sleep.
        with self.store._connect() as db:
            db.execute(
                "UPDATE creature_invitations SET expires_at='2000-01-01T00:00:00+00:00' WHERE invitation_id=?",
                (expired.invitation_id,),
            )
        with self.assertRaises(PermissionError):
            self.store.register_with_invitation(
                "expired@example.com", "a-very-long-member-password", "Expired", expired.token
            )

        revoked = self.store.issue_invitation(self.owner.user_id)
        self.assertTrue(self.store.revoke_invitation(self.owner.user_id, revoked.invitation_id))
        with self.assertRaises(PermissionError):
            self.store.register_with_invitation(
                "revoked@example.com", "a-very-long-member-password", "Revoked", revoked.token
            )

    def test_login_and_session_revocation(self) -> None:
        invite = self.store.issue_invitation(self.owner.user_id)
        member = self.store.register_with_invitation(
            "member@example.com", "a-very-long-member-password", "Member", invite.token
        )
        self.assertIsNone(self.store.authenticate("member@example.com", "wrong-password"))
        authenticated = self.store.authenticate(
            "MEMBER@example.com", "a-very-long-member-password"
        )
        self.assertEqual(authenticated.user_id, member.user_id)
        token, _expires = self.store.create_session(member.user_id)
        self.assertEqual(self.store.resolve_session(token).user_id, member.user_id)
        self.assertTrue(self.store.revoke_session(token))
        self.assertIsNone(self.store.resolve_session(token))

    def test_user_can_revoke_own_sessions_but_not_another_users(self) -> None:
        invite = self.store.issue_invitation(self.owner.user_id)
        member = self.store.register_with_invitation(
            "member@example.com", "a-very-long-member-password", "Member", invite.token
        )
        with self.assertRaises(PermissionError):
            self.store.revoke_all_sessions(member.user_id, self.owner.user_id)
        self.assertEqual(self.store.revoke_all_sessions(member.user_id, member.user_id), 0)

    def test_password_policy_and_generic_login_failure(self) -> None:
        with self.assertRaises(ValueError):
            self.store.bootstrap_owner(
                "other@example.com", "short", "Other"
            )
        self.assertIsNone(self.store.authenticate("missing@example.com", "some-long-password"))

    def test_invitation_tokens_are_not_stored_in_plaintext(self) -> None:
        invite = self.store.issue_invitation(self.owner.user_id)
        with self.store._connect() as db:
            row = db.execute(
                "SELECT token_sha256 FROM creature_invitations WHERE invitation_id=?",
                (invite.invitation_id,),
            ).fetchone()
        self.assertNotEqual(row["token_sha256"], invite.token)
        self.assertEqual(len(row["token_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
