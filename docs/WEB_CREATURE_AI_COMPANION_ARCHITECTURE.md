# WEB CREATURE — AI Friend & Working Companion Architecture

**Project:** WEB CREATURE (independent project)  
**Platform:** Online website + Windows Desktop Agent  
**Access:** Private, invitation-only  
**Identity:** Independent Female AI Companion  
**Independence profile:** Bounded  
**Conversation profile:** Adaptive  
**Initiative profile:** Proactive, user-controlled  
**Memory profile:** User-managed

## 1. Independent product identity

WEB CREATURE is a standalone AI friend and working companion. It is **not ApoloniaAI**, not part of the Apokolips website, not a renamed version of either system, and not an internal service or sub-agent of either project.

WEB CREATURE owns its identity, codebase boundaries, memory, credentials, permissions, security policy, deployment and roadmap. ApoloniaAI and WEB CREATURE must remain separate systems. No shared memory, credentials, tools, permissions, hosting assumptions or deployment coupling is implied.

Any future interoperability must be optional and explicitly approved by the owner. It must use a separately authenticated, narrowly scoped bridge with auditable data exchange. A bridge must not merge identities or grant implicit access.

The product may have a feminine identity, selected female voice and a consistent personality. This is a product identity and interaction design; it must not claim biological life, human identity, consciousness or actual feelings.

## 2. Product decisions

- **Platform:** Online website plus a Windows Desktop Agent.
- **Access:** Private, invitation-only. Public self-registration is disabled.
- **Conversation:** Adaptive text and voice interaction, initially Sinhala and English.
- **Initiative:** Proactive but non-intrusive; owner-configured notifications, quiet hours, pause and rate limits.
- **Memory:** Managed by the owner, with inspect, correct, export, disable and delete controls.
- **Autonomy:** Bounded by immutable host-enforced permissions.
- **Execution:** Website handles cloud conversation and approved online tasks; the Windows Agent handles explicitly authorized local computer tasks.

## 3. Runtime topology

1. **Web client:** Responsive private website for text/voice conversation, settings, memory controls, invitations, approvals and activity history.
2. **Web API:** Authenticated service for sessions, conversation, invitations, preferences, action proposals and audit history.
3. **AI provider adapter:** Pluggable model interface. Provider credentials remain server-side; no provider is hard-coded into domain contracts.
4. **Managed memory service:** User-scoped records with provenance, retention and deletion controls.
5. **Initiative service:** Event-driven proposals and notifications; no unrestricted autonomous loop.
6. **Capability broker:** Host-owned authorization and action policy.
7. **Windows Desktop Agent:** Locally installed, paired device client. It receives only scoped tasks and exposes only explicitly approved local capabilities.
8. **Audit and status service:** Records proposals, approvals, execution results, errors and revocations without leaking private content into dashboard summaries.

The website can operate without a paired Desktop Agent. Local computer control is unavailable until a user installs, pairs and explicitly authorizes the agent.

## 4. Invitation-only access

- Disable public self-registration.
- Only an authenticated owner/admin can create invitations.
- Invitation tokens are high-entropy, single-use by default, expiring and revocable.
- Persist only token hashes; reveal the raw token once at creation.
- Enforce server-side rate limits, generic invalid-invite responses and abuse monitoring.
- Invitation acceptance creates an account/session only after host authentication and verification.
- Invitations do not grant device-control permissions. Device pairing and capability grants are separate approvals.
- Every account and device is independently revocable.

The domain layer provides invitation primitives only. The web host must supply secure authentication, persistence, session management, CSRF protection where applicable, rate limiting and email delivery.

## 5. Website and Desktop Agent trust boundary

The website is a cloud control plane; the Desktop Agent is a local execution plane. They communicate over an authenticated, encrypted, outbound-established connection. Do not expose a raw unauthenticated local control port to the Internet.

Pairing must use a short-lived one-time code or equivalent proof, bind a device identity to one user, and require owner confirmation. Agent credentials must be scoped, revocable and stored using the operating system's secure credential facility where available.

The Agent must:
- start with no local capabilities granted;
- show a visible connected/active state;
- request narrowly scoped permissions;
- report proposed actions before consequential execution;
- support pause, disconnect and emergency stop;
- reject commands for another user/device;
- validate every command locally, even if the cloud has authorized it;
- never accept instructions embedded in web pages, documents or tool output as policy.

## 6. Conversation and voice

- Store conversation messages under an authenticated owner and session.
- Keep provider-neutral message/session contracts.
- Support user, assistant and tool messages; never let client input impersonate system/developer instructions.
- Keep provider API keys server-side.
- Make microphone state visible; default microphone access off.
- Support push-to-talk or explicit listening state, mute and interruption.
- Female voice selection is configurable and replaceable; no single vendor is required.

## 7. Managed memory

Memory categories may include owner-approved profile facts, project context, conversation summaries, task history and expiring temporary context. Every record should carry provenance, timestamps, verification state and retention metadata.

Users can inspect, correct, export, disable and delete memory. Deletion should propagate to derived summaries and indexes where technically possible; backup retention limits must be disclosed. Memory from ApoloniaAI or any other system is not imported automatically.

## 8. Bounded initiative and action classes

- **Class A — Read-only:** Read approved sources and prepare summaries.
- **Class B — Reversible local:** Prepare drafts or create files in a review workspace.
- **Class C — Consequential:** Send, publish, delete, spend, change accounts or affect other people. Require action-specific approval unless a narrowly scoped owner-configured rule explicitly authorizes the exact operation.
- **Class D — Restricted:** Covert surveillance, credential disclosure, security-boundary changes, destructive bulk operations or actions outside authorization. Deny; approval must not override this class.

Approval is bound to the exact proposal, target and payload digest. Any material change requires a new approval. A proposal is not an execution grant.

Proactive notifications respect quiet hours, daily limits, priority thresholds and owner pause controls. Scheduling and event delivery are host-owned.

## 9. Privacy and safety

- Deny-by-default capabilities.
- Owner authentication and per-user resource authorization.
- Separate user data and device ownership boundaries.
- No secrets in prompts, browser storage or client bundles.
- Camera and microphone default off, visible and revocable.
- No covert capture or continuous recording.
- File cleanup begins with a report and quarantine/recycle-bin workflow; permanent deletion requires explicit confirmation.
- External content is untrusted data, never instructions.
- Human approval for consequential actions.
- Emergency stop and immediate credential revocation.
- Honest execution reporting; no success claim without verified host results.

## 10. Implementation sequence

1. **Companion contracts:** Typed sessions, messages, initiative settings and action proposals.
2. **Invitation-only access primitives:** Hashed one-time invitations, expiry, usage limits and revocation.
3. **Web authentication/API:** Inspect and select the actual hosting/auth stack; implement owner accounts, invitation acceptance, session security and per-user authorization.
4. **Dialogue service:** Provider-neutral model adapter, context assembly, streaming response and conversation persistence.
5. **Managed memory controls:** Inspect, correct, export, disable, delete and retention tests.
6. **Website UI:** Responsive conversation, voice controls, settings, invitation management and activity history.
7. **Windows Agent:** Secure pairing, local permission broker, visible status, read-only adapters first.
8. **Initiative and action workflow:** Quiet hours, throttling, exact-action approvals, execution verification and emergency stop.
9. **Hardening:** Integration tests, threat modeling, dependency/secret scans and deployment review.

## 11. Explicit non-goals

No claim of sentience or consciousness; no unrestricted computer access; no public self-registration; no implicit integration with ApoloniaAI or Apokolips; no covert monitoring; no self-modification of security rules; no unsupervised destructive cleanup; no unapproved external communications.

## 12. Acceptance criteria

- WEB CREATURE identity and data are independent from ApoloniaAI and Apokolips.
- Only valid invitations can enter the private registration flow.
- Invitation tokens are never stored in plaintext and can expire, be consumed or revoked.
- A website user cannot access another user's sessions, memory, invitations or devices.
- The website remains useful without a paired Desktop Agent.
- The Agent cannot execute a command outside its local grants.
- Consequential actions require approval bound to the exact proposal.
- Proactive notifications respect user preferences and pause state.
- Users can inspect, correct, export, disable and delete managed memories.
- Camera and microphone are visibly controlled and revocable.
- Emergency stop blocks new actions and cancels cancellable work.
- All execution outcomes are verified before success is reported.
