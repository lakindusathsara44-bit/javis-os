from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.creature.accounts import AccountStore
from server.creature.http import create_auth_router


class PrivateAuthHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = AccountStore(Path(self.temp.name) / "auth.sqlite3")
        self.owner = self.store.bootstrap_owner(
            "owner@example.test", "a-long-owner-password-123", bootstrap_enabled=True
        )
        self.rate_events = []

        def rate_limiter(request, action, subject):
            self.rate_events.append((action, subject))

        app = FastAPI()
        app.include_router(
            create_auth_router(
                self.store,
                trusted_origins={"http://localhost"},
                rate_limiter=rate_limiter,
                cookie_secure=False,
            )
        )
        self.client = TestClient(app, base_url="http://localhost")
        self.headers = {
            "Origin": "http://localhost",
            "X-Web-Creature-Request": "1",
        }

    def tearDown(self) -> None:
        self.client.close()
        self.temp.cleanup()

    def test_login_me_and_logout_use_opaque_cookie_session(self) -> None:
        response = self.client.post(
            "/api/creature/auth/login",
            headers=self.headers,
            json={"email": "owner@example.test", "password": "a-long-owner-password-123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["account"]["role"], "owner")
        self.assertNotIn("token", response.json())
        cookie = response.headers.get("set-cookie", "")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=strict", cookie)

        me = self.client.get("/api/creature/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["account"]["account_id"], self.owner.account_id)

        logout = self.client.post("/api/creature/auth/logout", headers=self.headers)
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(self.client.get("/api/creature/auth/me").status_code, 401)

    def test_registration_requires_invitation_and_creates_member_session(self) -> None:
        invite = self.store.issue_invitation(self.owner.account_id)
        response = self.client.post(
            "/api/creature/auth/register",
            headers=self.headers,
            json={
                "invitation_token": invite.token,
                "email": "member@example.test",
                "password": "a-long-member-password-123",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["account"]["role"], "member")
        self.assertEqual(self.client.get("/api/creature/auth/me").status_code, 200)

    def test_member_cannot_issue_invitations(self) -> None:
        invite = self.store.issue_invitation(self.owner.account_id)
        self.client.post(
            "/api/creature/auth/register",
            headers=self.headers,
            json={
                "invitation_token": invite.token,
                "email": "member@example.test",
                "password": "a-long-member-password-123",
            },
        )
        response = self.client.post(
            "/api/creature/auth/invitations",
            headers=self.headers,
            json={},
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_can_issue_invitation_and_raw_token_is_returned_once(self) -> None:
        self.client.post(
            "/api/creature/auth/login",
            headers=self.headers,
            json={"email": "owner@example.test", "password": "a-long-owner-password-123"},
        )
        response = self.client.post(
            "/api/creature/auth/invitations",
            headers=self.headers,
            json={"max_uses": 1},
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["token"])
        self.assertEqual(body["max_uses"], 1)
        self.assertIn("Copy this token", body["notice"])

    def test_mutating_requests_require_exact_origin_and_custom_header(self) -> None:
        no_origin = self.client.post(
            "/api/creature/auth/login",
            json={"email": "owner@example.test", "password": "a-long-owner-password-123"},
        )
        self.assertEqual(no_origin.status_code, 403)
        wrong_origin = self.client.post(
            "/api/creature/auth/login",
            headers={
                "Origin": "https://attacker.example",
                "X-Web-Creature-Request": "1",
            },
            json={"email": "owner@example.test", "password": "a-long-owner-password-123"},
        )
        self.assertEqual(wrong_origin.status_code, 403)
        missing_custom_header = self.client.post(
            "/api/creature/auth/login",
            headers={"Origin": "http://localhost"},
            json={"email": "owner@example.test", "password": "a-long-owner-password-123"},
        )
        self.assertEqual(missing_custom_header.status_code, 403)

    def test_rate_limiter_is_called(self) -> None:
        response = self.client.post(
            "/api/creature/auth/login",
            headers=self.headers,
            json={"email": "owner@example.test", "password": "a-long-owner-password-123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(("login", "owner@example.test"), self.rate_events)

    def test_rate_limiter_failure_fails_closed(self) -> None:
        from fastapi import HTTPException

        def unavailable_limiter(request, action, subject):
            raise RuntimeError("rate limiter offline")

        app = FastAPI()
        app.include_router(
            create_auth_router(
                self.store,
                trusted_origins={"http://localhost"},
                rate_limiter=unavailable_limiter,
                cookie_secure=False,
            )
        )
        client = TestClient(app, base_url="http://localhost")
        response = client.post(
            "/api/creature/auth/login",
            headers=self.headers,
            json={"email": "owner@example.test", "password": "a-long-owner-password-123"},
        )
        self.assertEqual(response.status_code, 503)
        client.close()

    def test_production_cookie_mode_rejects_http_origin(self) -> None:
        with self.assertRaises(ValueError):
            create_auth_router(
                self.store,
                trusted_origins={"http://example.com"},
                rate_limiter=lambda request, action, subject: None,
                cookie_secure=True,
            )


if __name__ == "__main__":
    unittest.main()
