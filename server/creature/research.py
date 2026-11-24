"""Bounded, provenance-first research orchestration.

Search-provider integration is intentionally injected by the trusted host. This
module does not scrape arbitrary search results or follow redirects itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import re
from typing import Protocol

from .observation import TransportResponse, WebObservationPolicy


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Untrusted search metadata; only its URL is used to build a bounded plan."""
    title: str
    url: str
    snippet: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.title, str) or len(self.title) > 300:
            raise ValueError("search result title must be a string of at most 300 characters")
        if not isinstance(self.url, str) or not self.url.strip() or len(self.url) > 2048:
            raise ValueError("search result URL must contain 1-2048 characters")
        if not isinstance(self.snippet, str) or len(self.snippet) > 2000:
            raise ValueError("search result snippet must be a string of at most 2000 characters")


class SearchProvider(Protocol):
    def search(self, query: str, *, max_results: int) -> list[SearchResult] | tuple[SearchResult, ...]:
        """Return bounded untrusted results; host owns credentials, quotas and network policy."""
        ...


class WebTransport(Protocol):
    def fetch(self, url: str, *, timeout_seconds: float, max_bytes: int) -> TransportResponse:
        """Fetch one URL without automatic redirects under the host network policy."""
        ...


@dataclass(frozen=True, slots=True)
class ResearchPlan:
    question: str
    source_urls: tuple[str, ...]

    @classmethod
    def create(cls, question: str, source_urls: tuple[str, ...] | list[str]) -> "ResearchPlan":
        if not isinstance(question, str) or not question.strip() or len(question) > 1000:
            raise ValueError("question must contain 1-1000 characters")
        if not isinstance(source_urls, (tuple, list)) or not source_urls:
            raise ValueError("source_urls must be a non-empty list or tuple")
        if len(source_urls) > 20:
            raise ValueError("a plan may contain at most 20 source URLs")
        if any(not isinstance(url, str) or not url.strip() for url in source_urls):
            raise ValueError("every source URL must be a non-empty string")
        return cls(question.strip(), tuple(dict.fromkeys(url.strip() for url in source_urls)))


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    requested_url: str
    final_url: str
    domain: str
    title: str
    excerpt: str
    content_hash: str
    retrieved_at: str
    status_code: int
    content_type: str


@dataclass(frozen=True, slots=True)
class ResearchReport:
    question: str
    sources: tuple[SourceEvidence, ...]
    shared_statements: tuple[str, ...]
    unique_statements: tuple[tuple[str, tuple[str, ...]], ...]
    generated_at: str


class _VisibleHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self._hidden = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._hidden += 1
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._hidden:
            self._hidden -= 1
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if not value:
            return
        if self._in_title:
            self.title_parts.append(value)
        if not self._hidden:
            self.parts.append(value)


def _normalise_sentence(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w ]", " ", value.casefold())).strip()


def _sentences(text: str) -> list[str]:
    return [
        re.sub(r"\s+", " ", item).strip()
        for item in re.split(r"(?<=[.!?])\s+|\n+", text)
        if len(_normalise_sentence(item)) >= 40
    ]


def _extract(response: TransportResponse) -> tuple[str, str, str]:
    content_type = ""
    for key, value in response.headers.items():
        if key.lower() == "content-type":
            content_type = str(value).split(";", 1)[0].strip().lower()
            break
    if content_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
        raise ValueError(f"unsupported response content type: {content_type or 'missing'}")
    raw = response.body
    if not isinstance(raw, bytes):
        raise TypeError("transport response body must be bytes")
    if content_type == "text/plain":
        text = raw.decode("utf-8-sig", errors="replace")
        title = ""
    else:
        parser = _VisibleHTML()
        parser.feed(raw.decode("utf-8-sig", errors="replace"))
        text = "\n".join(parser.parts)
        title = " ".join(parser.title_parts)[:300]
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return title, text, content_type


class ResearchEngine:
    """Fetches only explicitly planned, allowlisted sources through an injected transport."""

    def __init__(
        self, policy: WebObservationPolicy, transport: WebTransport,
        search_provider: SearchProvider | None = None,
    ) -> None:
        if not isinstance(policy, WebObservationPolicy):
            raise TypeError("policy must be a WebObservationPolicy")
        if not callable(getattr(transport, "fetch", None)):
            raise TypeError("transport must provide a fetch method")
        if search_provider is not None and not callable(getattr(search_provider, "search", None)):
            raise TypeError("search_provider must provide a search method or be None")
        self.policy = policy
        self.transport = transport
        self.search_provider = search_provider

    def discover(self, question: str) -> ResearchPlan:
        """Ask the injected host provider for URLs, then apply the same strict allowlist."""
        if self.search_provider is None:
            raise RuntimeError("no host-approved search provider is configured")
        if not isinstance(question, str) or not question.strip() or len(question) > 1000:
            raise ValueError("question must contain 1-1000 characters")
        results = self.search_provider.search(question.strip(), max_results=self.policy.max_sources)
        if not isinstance(results, (list, tuple)) or len(results) > self.policy.max_sources:
            raise ValueError("search provider returned an invalid or oversized result set")
        urls = []
        for item in results:
            if not isinstance(item, SearchResult):
                raise TypeError("search provider results must be SearchResult values")
            urls.append(self.policy.validate_url(item.url))
        if not urls:
            raise ValueError("search provider returned no usable results")
        return ResearchPlan.create(question, urls)

    def run(self, plan: ResearchPlan) -> ResearchReport:
        if not isinstance(plan, ResearchPlan):
            raise TypeError("plan must be a ResearchPlan")
        if len(plan.source_urls) > self.policy.max_sources:
            raise ValueError("research plan exceeds configured source limit")
        collected: list[tuple[SourceEvidence, str]] = []
        for requested in plan.source_urls:
            safe_url = self.policy.validate_url(requested)
            response = self.transport.fetch(
                safe_url,
                timeout_seconds=float(self.policy.timeout_seconds),
                max_bytes=self.policy.max_response_bytes,
            )
            if not isinstance(response, TransportResponse):
                raise TypeError("transport must return a TransportResponse")
            for redirect in response.redirect_chain:
                self.policy.validate_url(redirect)
            final_url = self.policy.validate_url(response.final_url)
            if response.status_code < 200 or response.status_code >= 300:
                raise RuntimeError(f"source returned HTTP {response.status_code}: {final_url}")
            if len(response.body) > self.policy.max_response_bytes:
                raise ValueError("source response exceeds configured byte limit")
            title, text, content_type = _extract(response)
            if not text:
                raise ValueError(f"source contained no readable text: {final_url}")
            raw_text = text.encode("utf-8")
            from urllib.parse import urlsplit
            evidence = SourceEvidence(
                requested_url=safe_url,
                final_url=final_url,
                domain=urlsplit(final_url).hostname or "",
                title=title,
                excerpt=text[:4000],
                content_hash=hashlib.sha256(raw_text).hexdigest(),
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                status_code=response.status_code,
                content_type=content_type,
            )
            collected.append((evidence, text))

        statement_maps: list[dict[str, str]] = []
        for _, text in collected:
            mapping = {}
            for sentence in _sentences(text):
                mapping.setdefault(_normalise_sentence(sentence), sentence)
            statement_maps.append(mapping)
        shared_keys = set(statement_maps[0]) if statement_maps else set()
        for mapping in statement_maps[1:]:
            shared_keys.intersection_update(mapping)
        shared = tuple(statement_maps[0][key] for key in sorted(shared_keys))
        unique = []
        for index, mapping in enumerate(statement_maps):
            others = set().union(*(set(m) for j, m in enumerate(statement_maps) if j != index))
            statements = tuple(mapping[key] for key in sorted(set(mapping) - others))
            unique.append((collected[index][0].domain, statements))
        return ResearchReport(
            question=plan.question,
            sources=tuple(item[0] for item in collected),
            shared_statements=shared,
            unique_statements=tuple(unique),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
