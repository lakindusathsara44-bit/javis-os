"""Deterministic evidence classification and explicit human knowledge review.

Evidence overlap is a research signal, not proof of truth. This module never
marks a finding verified automatically and never treats web content as policy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
import re

from .research import ResearchReport


class EvidenceLevel(StrEnum):
    CORROBORATED = "corroborated"
    SINGLE_SOURCE = "single_source"


class ReviewDecision(StrEnum):
    VERIFIED = "verified"
    REJECTED = "rejected"


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w ]", " ", value.casefold())).strip()


@dataclass(frozen=True, slots=True)
class EvidenceFinding:
    finding_id: str
    statement: str
    evidence_level: EvidenceLevel
    source_domains: tuple[str, ...]
    source_hashes: tuple[str, ...]
    verified: bool = False


@dataclass(frozen=True, slots=True)
class KnowledgeReview:
    finding_id: str
    decision: ReviewDecision
    reviewer: str
    rationale: str
    reviewed_at: str


class ResearchVerifier:
    """Classifies source overlap and creates explicit reviewer decisions."""

    def evaluate(self, report: ResearchReport) -> tuple[EvidenceFinding, ...]:
        if not isinstance(report, ResearchReport):
            raise TypeError("report must be a ResearchReport")
        findings: dict[str, EvidenceFinding] = {}
        all_domains = tuple(dict.fromkeys(source.domain for source in report.sources))
        all_hashes = tuple(dict.fromkeys(source.content_hash for source in report.sources))
        for statement in report.shared_statements:
            key = _normalise(statement)
            if not key:
                continue
            finding_id = hashlib.sha256(key.encode("utf-8")).hexdigest()
            findings[finding_id] = EvidenceFinding(
                finding_id, statement, EvidenceLevel.CORROBORATED, all_domains, all_hashes, False
            )
        source_by_domain: dict[str, list[str]] = {}
        for source in report.sources:
            source_by_domain.setdefault(source.domain, []).append(source.content_hash)
        for domain, statements in report.unique_statements:
            for statement in statements:
                key = _normalise(statement)
                if not key:
                    continue
                finding_id = hashlib.sha256(key.encode("utf-8")).hexdigest()
                findings.setdefault(
                    finding_id,
                    EvidenceFinding(
                        finding_id, statement, EvidenceLevel.SINGLE_SOURCE,
                        (domain,), tuple(dict.fromkeys(source_by_domain.get(domain, ()))),
                        False,
                    ),
                )
        return tuple(findings[key] for key in sorted(findings))

    def review(
        self,
        finding: EvidenceFinding,
        decision: ReviewDecision,
        *,
        reviewer: str,
        rationale: str,
    ) -> KnowledgeReview:
        if not isinstance(finding, EvidenceFinding):
            raise TypeError("finding must be an EvidenceFinding")
        if not isinstance(decision, ReviewDecision):
            raise TypeError("decision must be a ReviewDecision")
        if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 120:
            raise ValueError("reviewer must contain 1-120 characters")
        if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 2000:
            raise ValueError("rationale must contain 1-2000 characters")
        return KnowledgeReview(
            finding_id=finding.finding_id,
            decision=decision,
            reviewer=reviewer.strip(),
            rationale=rationale.strip(),
            reviewed_at=datetime.now(timezone.utc).isoformat(),
        )


def review_to_dict(review: KnowledgeReview) -> dict[str, str]:
    """Return a JSON-safe immutable review snapshot for persistence."""
    if not isinstance(review, KnowledgeReview):
        raise TypeError("review must be a KnowledgeReview")
    value = asdict(review)
    value["decision"] = review.decision.value
    return value
