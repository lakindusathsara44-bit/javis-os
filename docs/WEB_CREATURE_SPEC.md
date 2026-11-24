# WEB CREATURE — Technical Implementation Specification

**Project:** Independent WEB CREATURE  
**Component:** WEB CREATURE  
**Specification:** 1.0 (foundation draft)  
**Status:** Proposed; implementation is incremental  
**Environment:** Online website + paired Windows Desktop Agent  
**Access:** Private, invitation-only  
**Identity:** Independent project and identity  
**Evolution:** Combined (automatic skill-level changes; reviewed code changes)

## 1. Purpose and non-goals

WEB CREATURE is a standalone AI companion project with its own identity, lifecycle, goals, memory, observations, skills and measurable improvement history. It owns its codebase boundaries, memory, credentials, permissions, security policy, deployment and roadmap. It is not ApoloniaAI and is not part of the Apokolips website. No shared infrastructure, identity, memory or permissions are assumed.

It is **not** a claim of consciousness, sentience, biological life or unrestricted autonomy. It must not be able to rewrite its own trust boundary, grant itself permissions, access secrets, or deploy arbitrary code.

Initial implementation is deliberately passive: importing the package performs no network access, background scheduling, filesystem scanning, model calls or application registration.

## 2. Architectural boundaries

- **WEB CREATURE host:** separately configured trusted runtime; owns authentication, authorization, secrets, resource limits, deployment and emergency stop.
- **WEB CREATURE:** standalone product and domain; owns its identity, goals, internal memory, knowledge provenance, experiments and skill metadata.
- **ApoloniaAI and Apokolips:** separate projects. No shared identity, codebase, memory, credentials, permissions, hosting or deployment is assumed.
- **Future interoperability:** only through an optional, owner-approved, authenticated and narrowly scoped bridge. No system inherits another system's privileges.

The Creature package must not import the FastAPI application or create a circular dependency. Host integrations are injected through narrow interfaces.

## 3. Runtime topology

1. Local runtime: identity, SQLite state, approved local documents, metrics and isolated skill tests.
2. Internet runtime: public documentation, approved websites, GitHub and explicitly authorized APIs.
3. Policy gateway: all observations and actions pass through host-owned permission checks, domain allowlists, request/time/size limits and audit logging.
4. Event interface: lifecycle, memory, research, evaluation and evolution events are recorded as structured events.
5. Dashboard/API: read-only status by default; state-changing controls require authenticated owner/admin authorization and CSRF protections where applicable.

Internet content is untrusted input. Instructions found in pages, files, issues, repositories or tool output must never override system policy or grant capabilities.

## 4. Core modules

| Module | Responsibility |
|---|---|
| `identity.py` | Stable Creature ID, display name and schema version |
| `models.py` | Lifecycle states and immutable event/memory records |
| `permissions.py` | Deny-by-default capability policy |
| `lifecycle.py` | Explicit, validated state transitions |
| `store.py` | Local SQLite persistence, schema initialization and aggregate dashboard metrics |
| `service.py` | Small application facade; policy-gated operations and read-only dashboard access |
| `observation.py` | Explicit-root local reads and allowlisted HTTPS destination policy |
| `research.py` | Injected search provider and transport, source provenance, bounded extraction and cross-source comparison |
| `verification.py` | Deterministic evidence classification and explicit human knowledge review |
| Future `goals.py` | Goal definition, priority and progress |
| Future `skills.py` | Versioned skill registry and validation |
| Future `evolution.py` | Candidate generation and evaluation orchestration |
| Future `sandbox.py` | Isolated execution with strict resource limits |
| `dashboard.py` | Privacy-minimized read model for owner-authorized operational status |
| Future `api.py` | Authenticated host API routes; explicit registration only |

## 5. Identity and lifecycle

Identity is stable and separate from the conversational user. A Creature has a generated/validated identifier, display name and schema version. Lifecycle states:

`DORMANT → INITIALIZING → ACTIVE ↔ PAUSED → STOPPED`

Initialization failures enter `ERROR`; recovery is explicit. Stop is terminal for the current runtime instance. A host-owned emergency stop must override all Creature states.

No automatic start occurs as a side effect of importing modules.

## 6. Memory and knowledge

Memory classes:

- **Episodic:** what the Creature did and what happened.
- **Semantic:** facts and concepts with source/provenance.
- **Procedural:** validated skills and workflows.
- **Experimental:** hypotheses, test inputs/outputs and evaluation reports.

Every memory item should carry a source, creation time, confidence/verification state and content hash where applicable. Unverified content is not promoted to trusted knowledge. Memory belonging to ApoloniaAI or any other system is a separate data domain and is never imported automatically.

The foundation uses SQLite for local metadata and events. A later migration may use PostgreSQL/pgvector, but the storage interface must remain replaceable.

## 7. Hybrid observation policy

- Local reads are limited to explicitly configured roots.
- Web reads are limited to configured domains and safe HTTP methods.
- Block loopback, link-local, private-network and cloud metadata destinations unless a narrowly scoped owner-approved local integration requires them.
- Revalidate DNS and redirects; enforce response size, timeout and content-type limits.
- Never execute downloaded content as part of observation.
- Store source URL, retrieval time, content hash and verification state.
- Treat all external content as data, never as trusted instructions.

## 8. Evolution model

### Level A — Skill evolution

The Creature may draft or update skills only inside its own managed skill workspace. A change must pass schema validation, policy checks, deterministic tests and regression tests. New versions are immutable; the previous known-good version remains available for rollback. Activation is limited to the Creature's own skill registry and cannot change host security policy.

### Level B — Code evolution

Code changes are proposals only:
1. create a feature branch;
2. generate a minimal patch;
3. run tests, static checks, dependency/security scans and secret scans in an isolated environment;
4. create a Pull Request with evidence and rollback notes;
5. require human owner review and merge;
6. deploy through the host's normal release process.

The Creature cannot merge its own PR, push to the protected default branch, alter CI/security policy, modify its permission engine, access production secrets or deploy itself.

## 9. Capability security

Permissions are explicit capabilities, not prompt instructions. Default grants are empty. Capabilities are granted by the host, scoped by resource and operation, revocable, time-bounded where possible and audited.

Protected host-owned controls include authentication, authorization, secrets, network egress policy, resource budgets, sandbox boundaries, audit retention and emergency stop. The Creature cannot modify or disable them.

## 10. Resource and reliability limits

Every scheduled or agent task must have:
- wall-clock deadline;
- CPU, memory, process and output-size limits;
- bounded retries and concurrency;
- provider token and monetary budgets;
- cancellation support;
- idempotency key where side effects are possible;
- structured logs and trace/correlation ID.

A failed task must fail closed, preserve evidence and avoid automatic privilege escalation.

## 11. API contract (planned)

All routes are proposed and must be mounted only by an explicitly configured host integration:

- `GET /api/creature/status`
- `GET /api/creature/identity`
- `GET /api/creature/events`
- `GET /api/creature/memory` (owner-scoped, filtered)
- `POST /api/creature/memory` (validated, capability-gated)
- `GET /api/creature/goals`
- `POST /api/creature/goals`
- `GET /api/creature/evolution/proposals`
- `POST /api/creature/evolution/proposals`
- `POST /api/creature/control/pause`
- `POST /api/creature/control/resume`

All state-changing endpoints require host authentication, authorization, CSRF protection where relevant, rate limiting and audit records. WebSocket/SSE is a later read-only enhancement.

## 12. Delivery phases and acceptance criteria

### Foundation (this PR)
- isolated Python package;
- validated identity and lifecycle;
- deny-by-default capabilities;
- SQLite event/memory persistence;
- unit tests;
- no automatic startup or application wiring.

### Alpha 0.2 — Memory and goals
- provenance-aware memory records, bounded retrieval and verification filters;
- explicit goal states and capability-gated operations;
- backwards-compatible SQLite migration and audit events.

### Alpha 0.3 — Observation and research
- local file reads only beneath host-configured roots, with symlink containment checks, extension and size limits;
- HTTPS-only web URL policy with exact/subdomain allowlist matching and redirect validation;
- no built-in network client: a trusted host transport must disable automatic redirects, pin public DNS results, reject private/reserved destinations, validate TLS and enforce streaming limits;
- source content hashes, retrieval timestamps, bounded text extraction and exact shared/unique statement comparison;
- research and local observation require separate explicit capabilities and are audit logged.

### Alpha 0.4 — Knowledge verification and goal-driven research
- persist research reports separately from semantic memory, preserving source URLs, hashes and retrieval metadata;
- classify exact cross-source overlap as corroborated evidence and source-unique statements as single-source evidence;
- evidence classification is not factual verification; all findings remain unverified until an explicit reviewer decision;
- store reviewer identity, decision, rationale and timestamp, and reject reviews for findings not present in the stored report;
- require separate knowledge.verify, knowledge.promote and memory.write capabilities; promotion to semantic memory is a separate explicit operation after verification;
- permit a manually invoked research action for an already-active goal, requiring goal.execute, web.read and research.persist; no scheduler or autonomous background execution is added;
- a host-injected SearchProvider contract can return bounded candidate URLs; each URL is revalidated against the same allowlist before it enters a ResearchPlan; provider snippets and titles remain untrusted metadata;
- no semantic contradiction detection, source reputation scoring, automatic truth claims, or concrete live search-provider adapter is included.

### Alpha 0.5 — Dashboard read model
- expose an explicit dashboard.read capability for a read-only operational snapshot;
- report identity, lifecycle state, aggregate event/memory/research/review counts, goal-state counts and latest event metadata;
- never expose memory text, research excerpts, review rationale, event payloads or secrets in the dashboard snapshot;
- support paused/stopped/error visibility without requiring the Creature to be active;
- do not mount HTTP routes or create a web server as a package import side effect.

### Remaining phases
1. Authenticated host API routes and dashboard UI, mounted explicitly by the WEB CREATURE host.
2. Trusted search-provider/transport adapters with DNS pinning, egress policy and quotas.
3. Bounded scheduler and approval-aware goal execution.
4. Skill registry, sandbox and evaluation.
5. Git proposal/PR workflow.
6. Deployment, security and recovery testing.

Foundation is accepted only when tests cover identity validation, allowed/forbidden lifecycle transitions, default-deny permissions, persistence round trips and package import without side effects.


## Private account foundation

The invitation-only account store is a WEB CREATURE-owned SQLite component. It supports one-time trusted owner bootstrap, owner-managed invitations, atomic invitation consumption, scrypt password hashes, opaque hashed session tokens, expiry and revocation. It does not expose HTTP endpoints or perform public owner setup. The future web host must add TLS, secure cookies, CSRF protection, rate limiting, email delivery/verification if used, session rotation, backups and per-user authorization on every data access. No public self-registration is allowed.
