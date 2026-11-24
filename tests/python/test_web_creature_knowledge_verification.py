from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.creature import (
    CapabilityPolicy, CreatureGoal, CreatureIdentity, CreatureService, CreatureStore,
    EvidenceLevel, ResearchReport, ResearchVerifier, ReviewDecision, SourceEvidence,
)


def sample_report() -> ResearchReport:
    shared = "The documented standard requires an explicit and independently reviewable approval process."
    unique = "This source additionally describes a separate implementation detail for local operators."
    sources = (
        SourceEvidence("https://one.example.org/a", "https://one.example.org/a", "one.example.org",
                       "Source one", shared + " " + unique, "a" * 64, "2026-11-24T00:00:00+00:00", 200, "text/plain"),
        SourceEvidence("https://two.example.org/b", "https://two.example.org/b", "two.example.org",
                       "Source two", shared, "b" * 64, "2026-11-24T00:00:00+00:00", 200, "text/plain"),
    )
    return ResearchReport(
        question="What approval controls are described?",
        sources=sources,
        shared_statements=(shared,),
        unique_statements=(("one.example.org", (unique,)), ("two.example.org", ())),
        generated_at="2026-11-24T00:00:00+00:00",
    )


class ResearchVerifierTests(unittest.TestCase):
    def test_overlap_is_a_signal_not_automatic_verification(self) -> None:
        findings = ResearchVerifier().evaluate(sample_report())
        shared = next(item for item in findings if item.evidence_level == EvidenceLevel.CORROBORATED)
        unique = next(item for item in findings if item.evidence_level == EvidenceLevel.SINGLE_SOURCE)
        self.assertFalse(shared.verified)
        self.assertFalse(unique.verified)
        self.assertEqual(len(shared.source_hashes), 2)
        self.assertEqual(len(unique.source_hashes), 1)

    def test_review_requires_reviewer_and_rationale(self) -> None:
        finding = ResearchVerifier().evaluate(sample_report())[0]
        verifier = ResearchVerifier()
        with self.assertRaises(ValueError):
            verifier.review(finding, ReviewDecision.VERIFIED, reviewer="", rationale="Checked")
        review = verifier.review(
            finding, ReviewDecision.VERIFIED,
            reviewer="owner", rationale="Compared both original source documents.",
        )
        self.assertEqual(review.decision, ReviewDecision.VERIFIED)


class ResearchPersistenceTests(unittest.TestCase):
    def test_report_and_review_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CreatureStore(Path(directory) / "creature.sqlite3")
            store.initialize()
            report = sample_report()
            research_id = store.save_research_report(report)
            saved = store.get_research_report(research_id)
            self.assertEqual(saved["question"], report.question)
            self.assertEqual(len(saved["report"]["sources"]), 2)
            finding = ResearchVerifier().evaluate(report)[0]
            review = ResearchVerifier().review(
                finding, ReviewDecision.VERIFIED, reviewer="owner",
                rationale="Source documents checked manually.",
            )
            review_id = store.save_knowledge_review(research_id, review)
            self.assertGreater(review_id, 0)
            self.assertEqual(store.list_knowledge_reviews(research_id)[0]["decision"], "verified")

    def test_rejects_review_for_unknown_finding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = CreatureStore(Path(directory) / "creature.sqlite3")
            store.initialize()
            research_id = store.save_research_report(sample_report())
            from server.creature import KnowledgeReview
            review = KnowledgeReview("f" * 64, ReviewDecision.VERIFIED, "owner", "Reviewed", "2026-11-24T00:00:00+00:00")
            with self.assertRaises(ValueError):
                store.save_knowledge_review(research_id, review)


class KnowledgePromotionTests(unittest.TestCase):
    def test_memory_promotion_requires_review_and_separate_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            grants = frozenset({"memory.write", "knowledge.verify", "knowledge.promote"})
            service = CreatureService(
                CreatureIdentity("web-creature-001"),
                CreatureStore(Path(directory) / "creature.sqlite3"),
                CapabilityPolicy(grants),
            )
            service.initialize()
            research_id = service.store.save_research_report(sample_report())
            finding = service.evaluate_research(research_id)[0]
            with self.assertRaises(PermissionError):
                service.promote_verified_claim_to_memory(research_id, finding.finding_id)
            service.review_knowledge_claim(
                research_id, finding.finding_id, ReviewDecision.VERIFIED,
                reviewer="owner", rationale="Reviewed the primary source documents.",
            )
            memory_id = service.promote_verified_claim_to_memory(research_id, finding.finding_id)
            self.assertGreater(memory_id, 0)
            memories = service.store.list_memory(verification_status="verified")
            self.assertEqual(len(memories), 1)
            self.assertEqual(memories[0]["source_kind"], "web")


if __name__ == "__main__":
    unittest.main()
