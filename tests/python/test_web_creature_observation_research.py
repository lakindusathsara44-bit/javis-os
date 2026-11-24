from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from server.creature import (
    CapabilityPolicy, CreatureIdentity, CreatureService, CreatureStore,
    LocalFileObserver, LocalFilePolicy, ResearchEngine, ResearchPlan,
    TransportResponse, WebObservationPolicy,
)


class FakeTransport:
    def __init__(self, responses: dict[str, TransportResponse]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def fetch(self, url: str, *, timeout_seconds: float, max_bytes: int) -> TransportResponse:
        self.calls.append(url)
        if url not in self.responses:
            raise AssertionError(f"unexpected URL: {url}")
        return self.responses[url]


def response(url: str, body: str, content_type: str = "text/plain", **kwargs) -> TransportResponse:
    return TransportResponse(
        status_code=kwargs.get("status_code", 200),
        final_url=kwargs.get("final_url", url),
        headers={"Content-Type": content_type},
        body=body.encode("utf-8"),
        redirect_chain=kwargs.get("redirect_chain", ()),
    )


class LocalObservationTests(unittest.TestCase):
    def test_reads_only_approved_text_file_and_hashes_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "notes.md"
            target.write_text("Approved local note", encoding="utf-8")
            observer = LocalFileObserver(LocalFilePolicy((root,)))
            item = observer.read_text(target)
            self.assertEqual(item.relative_path, "notes.md")
            self.assertEqual(item.content, "Approved local note")
            self.assertEqual(len(item.content_hash), 64)

    def test_rejects_file_outside_approved_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as other:
            target = Path(other) / "private.txt"
            target.write_text("not allowed", encoding="utf-8")
            observer = LocalFileObserver(LocalFilePolicy((Path(directory),)))
            with self.assertRaises(PermissionError):
                observer.read_text(target)

    def test_rejects_unapproved_extension_and_oversized_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "secret.exe"
            binary.write_text("data", encoding="utf-8")
            too_large = root / "large.txt"
            too_large.write_text("123456789", encoding="utf-8")
            observer = LocalFileObserver(LocalFilePolicy((root,), max_file_bytes=8))
            with self.assertRaises(PermissionError):
                observer.read_text(binary)
            with self.assertRaises(ValueError):
                observer.read_text(too_large)

    def test_rejects_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as other:
            root, outside = Path(directory), Path(other) / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            link = root / "escape.txt"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable on this platform")
            observer = LocalFileObserver(LocalFilePolicy((root,)))
            with self.assertRaises(PermissionError):
                observer.read_text(link)


class WebPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = WebObservationPolicy(frozenset({"example.org"}), max_sources=3, max_response_bytes=1000)

    def test_accepts_https_allowlisted_host_and_normalizes(self) -> None:
        self.assertEqual(
            self.policy.validate_url("https://docs.example.org/guide#section"),
            "https://docs.example.org/guide",
        )

    def test_rejects_http_credentials_ip_and_unlisted_domains(self) -> None:
        for url in (
            "http://example.org/",
            "https://user:pass@example.org/",
            "https://127.0.0.1/",
            "https://example.net/",
            "https://example.org:8443/",
        ):
            with self.subTest(url=url), self.assertRaises((PermissionError, ValueError)):
                self.policy.validate_url(url)

    def test_redirect_chain_is_checked_before_report_is_returned(self) -> None:
        url = "https://example.org/start"
        transport = FakeTransport({
            url: response(
                url, "safe text", redirect_chain=("https://attacker.invalid/collect",)
            )
        })
        engine = ResearchEngine(self.policy, transport)
        with self.assertRaises(PermissionError):
            engine.run(ResearchPlan.create("Check this source", [url]))

    def test_final_url_must_remain_allowlisted(self) -> None:
        url = "https://example.org/start"
        transport = FakeTransport({
            url: response(url, "safe text", final_url="https://attacker.invalid/page")
        })
        with self.assertRaises(PermissionError):
            ResearchEngine(self.policy, transport).run(ResearchPlan.create("Check", [url]))

    def test_rejects_oversized_and_non_text_responses(self) -> None:
        url = "https://example.org/a"
        big = response(url, "x" * 1001)
        with self.assertRaises(ValueError):
            ResearchEngine(self.policy, FakeTransport({url: big})).run(ResearchPlan.create("Check", [url]))
        binary = response(url, "not text", "application/octet-stream")
        with self.assertRaises(ValueError):
            ResearchEngine(self.policy, FakeTransport({url: binary})).run(ResearchPlan.create("Check", [url]))

    def test_plan_is_bounded_and_deduplicated(self) -> None:
        plan = ResearchPlan.create("A useful research question", [
            "https://example.org/a", "https://example.org/a", "https://example.org/b",
        ])
        self.assertEqual(len(plan.source_urls), 2)
        with self.assertRaises(ValueError):
            ResearchPlan.create("Question", [f"https://example.org/{i}" for i in range(21)])


class ResearchEngineTests(unittest.TestCase):
    def test_extracts_html_provenance_and_compares_source_statements(self) -> None:
        shared = "A carefully documented shared statement that is long enough to be compared."
        one = "A unique finding from the first source that is not present in the second source."
        two = "A separate unique finding from the second source that differs from the first."
        first_url, second_url = "https://example.org/one", "https://docs.example.org/two"
        transport = FakeTransport({
            first_url: response(first_url, f"<html><head><title>First source</title></head><body><p>{shared}</p><p>{one}</p><script>ignore this</script></body></html>", "text/html"),
            second_url: response(second_url, f"<html><head><title>Second source</title></head><body><p>{shared}</p><p>{two}</p></body></html>", "text/html"),
        })
        report = ResearchEngine(
            WebObservationPolicy(frozenset({"example.org"}), max_sources=2), transport
        ).run(ResearchPlan.create("Compare the two sources", [first_url, second_url]))
        self.assertEqual(len(report.sources), 2)
        self.assertEqual(report.sources[0].title, "First source")
        self.assertNotIn("ignore this", report.sources[0].excerpt)
        self.assertIn(shared, report.shared_statements)
        self.assertEqual(len(report.unique_statements), 2)
        self.assertTrue(all(len(source.content_hash) == 64 for source in report.sources))

    def test_transport_is_not_called_for_disallowed_url(self) -> None:
        transport = FakeTransport({})
        engine = ResearchEngine(WebObservationPolicy(frozenset({"example.org"})), transport)
        with self.assertRaises(PermissionError):
            engine.run(ResearchPlan.create("Research", ["https://not-allowed.invalid/"]))
        self.assertEqual(transport.calls, [])


class CreatureServiceObservationTests(unittest.TestCase):
    def test_local_and_web_observation_require_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / "approved.txt"
            file.write_text("approved", encoding="utf-8")
            observer = LocalFileObserver(LocalFilePolicy((root,)))
            url = "https://example.org/info"
            engine = ResearchEngine(
                WebObservationPolicy(frozenset({"example.org"})),
                FakeTransport({url: response(url, "A sufficiently long source statement for research evidence.")}),
            )
            service = CreatureService(
                CreatureIdentity("web-creature-001"),
                CreatureStore(root / "creature.sqlite3"),
                CapabilityPolicy(frozenset()),
                local_observer=observer,
                research_engine=engine,
            )
            service.initialize()
            with self.assertRaises(PermissionError):
                service.observe_local_file(str(file))
            with self.assertRaises(PermissionError):
                service.research(ResearchPlan.create("Question", [url]))

    def test_approved_observations_are_audited_without_storing_file_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / "approved.txt"
            file.write_text("private note body", encoding="utf-8")
            url = "https://example.org/info"
            service = CreatureService(
                CreatureIdentity("web-creature-001"),
                CreatureStore(root / "creature.sqlite3"),
                CapabilityPolicy(frozenset({"local.read", "web.read"})),
                local_observer=LocalFileObserver(LocalFilePolicy((root,))),
                research_engine=ResearchEngine(
                    WebObservationPolicy(frozenset({"example.org"})),
                    FakeTransport({url: response(url, "A sufficiently long source statement for research evidence.")}),
                ),
            )
            service.initialize()
            local = service.observe_local_file(str(file))
            report = service.research(ResearchPlan.create("Question", [url]))
            self.assertEqual(local.content, "private note body")
            self.assertEqual(len(report.sources), 1)
            events = service.store.list_events()
            local_event = next(item for item in events if item["event_type"] == "observation.local_file")
            self.assertNotIn("private note body", str(local_event["payload"]))
            self.assertTrue(any(item["event_type"] == "research.completed" for item in events))

    def test_observation_requires_explicit_host_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = CreatureService(
                CreatureIdentity("web-creature-001"),
                CreatureStore(Path(directory) / "creature.sqlite3"),
                CapabilityPolicy(frozenset({"local.read", "web.read"})),
            )
            service.initialize()
            with self.assertRaises(RuntimeError):
                service.observe_local_file(str(Path(directory) / "missing.txt"))
            with self.assertRaises(RuntimeError):
                service.research(ResearchPlan.create("Question", ["https://example.org/"]))


if __name__ == "__main__":
    unittest.main()
