# WEB CREATURE — Technical Implementation Specification

**Project:** APOLONIA ALPHA  
**Component:** WEB CREATURE  
**Specification:** 1.0 (foundation draft)  
**Status:** Proposed; implementation is incremental  
**Environment:** Hybrid (local + permitted internet resources)  
**Identity:** Independent entity under APOLONIA ALPHA  
**Evolution:** Combined (automatic skill-level changes; reviewed code changes)

## 1. Purpose and non-goals

WEB CREATURE is an autonomous software agent subsystem with its own identity, lifecycle, goals, memory, observations, skills and measurable improvement history. It is independently addressable and owns its internal state, while using APOLONIA ALPHA's approved model, storage and tool infrastructure.

It is **not** a claim of consciousness, sentience, biological life or unrestricted autonomy. It must not be able to rewrite its own trust boundary, grant itself permissions, access secrets, or deploy arbitrary code.

Initial implementation is deliberately passive: importing the package performs no network access, background scheduling, filesystem scanning, model calls or application registration.

## 2. Architectural boundaries

- **APOLONIA ALPHA:** trusted host; owns authentication, authorization, secrets, resource limits, deployment and emergency stop.
- **WEB CREATURE:** independent domain subsystem; owns its identity, goals, internal memory, knowledge provenance, experiments and skill metadata.
- **APOLONIA AI:** conversational interface and collaborator. It calls Creature APIs through authenticated, scoped interfaces; it does not share unrestricted memory or credentials.
- **Existing JARVIS OS facilities:** candidate infrastructure to reuse after code-level review (model router, MCP Hub, learning/promotion, improvement experiments and sandbox). No existing privileged mode is automatically inherited.

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
| `store.py` | Local SQLite persistence and schema initialization |
| `service.py` | Small application facade; policy-gated operations |
| Future `observation.py` | Local and allowlisted web observations |
| Future `research.py` | Source collection, provenance and verification |
| Future `goals.py` | Goal definition, priority and progress |
| Future `skills.py` | Versioned skill registry and validation |
| Future `evolution.py` | Candidate generation and evaluation orchestration |
| Future `sandbox.py` | Isolated execution with strict resource limits |
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

Every memory item should carry a source, creation time, confidence/verification state and content hash where applicable. Unverified content is not promoted to trusted knowledge. User-specific APOLONIA AI memory is a separate data domain; only explicitly authorized, minimized context may cross the boundary.

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

### Next phases
1. Host integration and configuration.
2. Memory retrieval, provenance and retention.
3. Goals and bounded scheduler.
4. Local/web observation adapters.
5. Skill registry, sandbox and evaluation.
6. Git proposal/PR workflow.
7. Authenticated API and dashboard.
8. deployment, security and recovery testing.

Foundation is accepted only when tests cover identity validation, allowed/forbidden lifecycle transitions, default-deny permissions, persistence round trips and package import without side effects.
