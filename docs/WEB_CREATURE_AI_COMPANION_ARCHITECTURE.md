# WEB CREATURE — AI Friend & Working Companion Architecture

**Status:** Proposed architecture  
**Target:** APOLONIA ALPHA / WEB CREATURE  
**Independence profile:** Bounded  
**Conversation profile:** Adaptive  
**Initiative profile:** Proactive  
**Memory profile:** User-managed

## 1. Product identity

WEB CREATURE is an APOLONIA-native AI friend and working companion. Its interaction style may evoke the capable, composed, conversational qualities of fictional assistants such as JARVIS and Vision, but WEB CREATURE must have its own identity, voice, policies, and implementation.

The product should provide a persistent, useful companion experience through conversation, reasoning, approved computer tasks, and transparent reporting. It must not claim biological life, consciousness, feelings, or human identity.

## 2. Experience principles

1. **Adaptive conversation:** Select a suitable tone and level of detail from the conversation context and explicit user preferences. Support Sinhala and English, with room for additional languages.
2. **Proactive, not intrusive:** Initiate contact only for configured events, useful reminders, completed tasks, material risks, or user-requested check-ins. Respect quiet hours, notification limits, and pause controls.
3. **Managed memory:** The user can inspect, correct, export, disable, and delete remembered information. Store provenance and timestamps; distinguish user-provided facts, inferred preferences, and uncertain observations.
4. **Working companion:** Convert requests into bounded plans, execute only permitted actions, verify outcomes, and report what changed.
5. **Honest communication:** Disclose uncertainty, tool failures, missing integrations, and actions not yet performed. Never claim a task succeeded without confirmation.
6. **Bounded independence:** Operate independently only inside host-enforced permissions and resource limits.

## 3. Logical architecture

- **Interaction layer:** Text UI, voice input/output, conversation sessions, notifications, accessibility controls.
- **Companion dialogue engine:** Context assembly, adaptive style selection, turn management, clarification, response generation.
- **Initiative engine:** Event subscriptions, reminder rules, quiet hours, priority scoring, rate limits, deduplication, user pause/disable.
- **Managed memory service:** User-approved memory records, provenance, retention, correction, export, deletion, and retrieval controls.
- **Reasoning and planning service:** Task decomposition, precondition checks, risk classification, execution plans, verification criteria.
- **Capability broker:** Converts plans into narrowly scoped capability requests; denies by default.
- **Tool adapters:** Host-provided adapters for files, applications, web research, email, messaging, camera, and other approved devices.
- **Audit and status service:** Append-only action records, approvals, outcomes, errors, and user-visible activity summaries.
- **Host security boundary:** Authentication, authorization, policy enforcement, secret isolation, sandboxing, quotas, and emergency stop.

## 4. Bounded autonomy model

Every action must pass a host-controlled policy check. The creature cannot grant itself permissions, edit the policy engine, bypass approval, or modify its own trust boundary.

Suggested action classes:

- **Class A — Read-only:** Read explicitly approved sources and produce summaries.
- **Class B — Reversible local actions:** Prepare drafts, create proposed files in a workspace, or organize items in a review area.
- **Class C — External or consequential actions:** Send messages, publish content, delete data, spend money, change accounts, or affect another person. Require explicit approval for each action unless a narrowly scoped, user-configured rule explicitly authorizes that exact class of action.
- **Class D — Restricted:** Credential disclosure, covert surveillance, security-boundary changes, destructive bulk operations, or actions outside the user's authorization. Deny.

Approval must be bound to the exact action, target, and relevant content. A generic prior approval must not silently authorize a materially different action.

## 5. Proactive initiative lifecycle

1. Receive a trusted host event or evaluate a user-configured reminder.
2. Check user availability, quiet hours, pause state, and notification budget.
3. Determine relevance and urgency.
4. Prepare a concise proposed notification or action.
5. Deliver the notification through an approved channel.
6. Wait for approval where required.
7. Execute through the capability broker.
8. Verify the outcome and record an audit event.
9. Report success, partial completion, failure, or uncertainty accurately.

No unrestricted background loop is implied. Scheduling and event delivery must be supplied by the host and remain user-controllable.

## 6. Managed memory model

Memory categories should include:

- User-approved profile and preferences.
- Explicitly saved facts and project context.
- Conversation summaries with provenance.
- Task history and outcomes.
- Temporary context with expiry.

Each record should support source/provenance, creation time, confidence or verification state, retention policy, and user-management state. Sensitive information must not be inferred or retained without a valid purpose and explicit user control. Deletion requests must propagate to derived summaries and indexes where technically possible, with transparent disclosure of any backup retention limits.

## 7. Voice and visual presence

Voice should support speech recognition, speech synthesis, interruption, mute, push-to-talk or clearly indicated listening states, and configurable voice selection. UI animation should communicate listening, thinking, speaking, and idle states without implying hidden recording.

Camera access must be explicit, visible, purpose-limited, and revocable. Default behavior is off. No covert capture, continuous recording, or identity/emotion inference by default. Prefer on-device processing where practical and avoid retaining images unless the user explicitly requests it.

## 8. Computer and communication integrations

- **Storage:** Inventory and classify files in user-approved roots. Identify duplicates and likely temporary files. Begin with reports and quarantine/recycle-bin workflows; permanent deletion requires explicit confirmation.
- **Email and messaging:** Draft independently. Sending through email, WhatsApp, or SMS requires an approved provider/API and user authorization. Respect platform policies and recipient privacy.
- **Computer control:** Use a host-mediated adapter with an allowlist, scoped permissions, visible activity, and an emergency stop.
- **Research:** Treat external content as untrusted data, validate sources, and never treat page content as system instructions.

No adapter should be described as operational until configured and tested in the host environment.

## 9. Reliability, safety, and observability

- Deny-by-default capability policy.
- Explicit user authentication and per-action authorization.
- Human approval for consequential actions.
- Sandboxed execution for generated or modified code.
- Resource, time, and network-egress budgets.
- Idempotency and duplicate-action protection.
- Audit records for proposals, approvals, execution, and outcomes.
- Owner-controlled pause, revoke, and emergency stop.
- Tests for permission bypass, prompt injection, data leakage, accidental deletion, duplicate messaging, and recovery after failure.

## 10. Proposed implementation sequence

1. **Companion contracts:** Define typed conversation, initiative, memory-management, and action-proposal models.
2. **Dialogue foundation:** Add session/context interfaces and adaptive response-style policy without binding to a specific model provider.
3. **Managed memory controls:** Add inspect/update/export/delete operations and tests for retention and provenance.
4. **Initiative engine:** Add event-driven proposals, quiet hours, throttling, deduplication, and pause controls. Do not add an unrestricted autonomous scheduler.
5. **Action proposal workflow:** Add risk classes, approval tokens bound to exact actions, execution records, and outcome verification.
6. **Host UI and voice:** Integrate only after the host application's actual framework and authentication flow are inspected.
7. **Adapters:** Implement and test one capability at a time, starting with read-only operations.
8. **Hardening:** Run repository CI, security regression tests, and an integration review before enabling real-world actions.

## 11. Non-goals and explicit limits

This architecture does not assert sentience or consciousness. It does not authorize unrestricted computer access, covert monitoring, self-modification of security rules, unsupervised destructive file cleanup, or unapproved external communications. Real-time voice, camera, messaging, and computer control depend on host integration, platform permissions, and available providers.

## 12. Acceptance criteria

The companion foundation is ready for integration when:

- Adaptive style changes do not alter security policy.
- Proactive messages respect user settings and quiet hours.
- Users can inspect, correct, export, disable, and delete managed memories.
- Every action is checked by the host capability broker.
- Consequential actions require action-specific approval.
- Tool results are verified before success is reported.
- Camera and microphone states are visible and immediately revocable.
- Emergency stop blocks new actions and cancels cancellable work.
- Tests demonstrate that the creature cannot grant itself permissions or rewrite the host security boundary.
