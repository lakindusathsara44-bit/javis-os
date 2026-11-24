"""WEB CREATURE subsystem for APOLONIA ALPHA.

Importing this package is intentionally side-effect free. The trusted host
must explicitly construct and initialize a CreatureService.
"""
from .identity import CreatureIdentity
from .lifecycle import CreatureLifecycle, CreatureState
from .models import CreatureGoal, CreatureMemory, GoalStatus
from .observation import LocalFileObserver, LocalFilePolicy, LocalObservation, TransportResponse, WebObservationPolicy
from .research import ResearchEngine, ResearchPlan, ResearchReport, SearchProvider, SearchResult, SourceEvidence, WebTransport
from .permissions import CapabilityPolicy
from .service import CreatureService
from .store import CreatureStore
from .verification import EvidenceFinding, EvidenceLevel, KnowledgeReview, ResearchVerifier, ReviewDecision

__all__ = [
    "CapabilityPolicy",
    "CreatureGoal",
    "CreatureIdentity",
    "CreatureLifecycle",
    "CreatureMemory",
    "CreatureService",
    "CreatureState",
    "CreatureStore",
    "EvidenceFinding",
    "EvidenceLevel",
    "KnowledgeReview",
    "ResearchVerifier",
    "ReviewDecision",
    "GoalStatus",
    "LocalFileObserver",
    "LocalFilePolicy",
    "LocalObservation",
    "ResearchEngine",
    "ResearchPlan",
    "ResearchReport",
    "SearchProvider",
    "SearchResult",
    "SourceEvidence",
    "TransportResponse",
    "WebObservationPolicy",
    "WebTransport",
]
