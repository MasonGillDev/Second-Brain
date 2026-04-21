# Enterprise Gamma — Agent Harness Taxonomy
**SLYD Group Inc. | Confidential | Working Draft v1**
*Author: Hayden | Session Date: April 2026*

---

## Purpose of this document

The Enterprise Gamma planning document names the mandate layer, the role-based tool ceiling, the trust/drift system, and AgentShield — but it does not yet name the composite that surrounds every agent and governs how it actually operates. That composite is the **harness**.

This document defines the harness as a first-class architectural concept, names the archetypes we will ship, specifies what each archetype contains, and draws the line between harness evolution (Gamma's concern) and model evolution (a separate, premium pathway tied to dedicated infrastructure).

Until the harness is named explicitly, every enterprise conversation about "how do your agents actually work" will be answered ad hoc. With it named, the answer becomes architectural.

---

## 1. What a harness is

A harness is the complete envelope around an agent. The model provides raw capability. The harness turns that capability into a governed, observable, improvable worker.

An Enterprise Gamma harness is composed of seven layers. An agent is never deployed without all seven — there is no such thing as a "harness-free" agent on the platform.

| # | Layer | What it governs |
|---|---|---|
| 1 | **Mandate binding** | Which cryptographically signed mandate this agent operates under, how the harness reads the mandate, how mandate changes propagate to the running agent |
| 2 | **Context construction** | What enters the context window, in what order, from which sources, filtered how. Includes knowledge-layer access, document retrieval scope, memory policy |
| 3 | **Reasoning scaffold** | The structural prompt that shapes how the agent breaks down work — plan-then-act, research-then-synthesize, propose-then-verify, and so on |
| 4 | **Tool binding** | Which tools from the agent's role ceiling are actually exposed to this specific agent, in what configurations, with what parameter constraints |
| 5 | **Enforcement hooks** | The required integration points with AgentShield — injection scanner pre-processing, pre-execution ledger writes, always-human guard evaluation, trust score event emission |
| 6 | **Evaluation hooks** | How the agent's outputs and behaviors are measured — what gets scored, against what rubric, feeding what part of the intelligence loop |
| 7 | **Feedback ingestion** | How drift events, human overrides, Red Team findings, and task outcomes flow back into harness tuning proposals |

The first five layers are runtime. Layers 6 and 7 are the loop that makes the harness a living artifact rather than a static configuration.

### What a harness is not

- Not a prompt. A prompt is one element inside Layer 3.
- Not a tool set. A tool set is one element inside Layer 4.
- Not a model. The model runs underneath the harness and can be swapped without harness changes.
- Not a mandate. The mandate is authority. The harness is how the agent operates within that authority.

### The versioning rule

Every harness is a versioned, cryptographically signed artifact. An agent runs on harness `research-v2.4.1`, not on "a research harness." Version promotions require human signature appropriate to the scope of the change (detailed in Section 4). Version history is written to the immutable ledger. Rollback is a first-class operation.

---

## 2. The archetype set

Five base archetypes cover the bulk of enterprise work. Specialized role surfaces (Marketing, Finance, Legal, HR) are built by layering domain context onto one of these base archetypes, not by inventing new ones.

| Archetype | Primary use | Autonomy posture |
|---|---|---|
| **Research** | Deep reading, synthesis, citation, analysis | Moderate — autonomous within information gathering; human confirmation on any produced claim that leaves the agent |
| **Execution** | Short, decisive actions inside narrow tool sets | Low — pre-execution verification is heavy; tool calls gated hard |
| **Orchestration** | Coordinating subagents, routing work, managing fleet-level tasks | Low on action, high on coordination — can spawn and direct within authorization, cannot execute downstream tool work directly |
| **Conversational** | Human-facing interfaces, clarification, escalation routing | Low — default posture is ask, not act |
| **Generative** | Content, drafts, creative output | Moderate — autonomous within drafting; human confirmation gates on publication or external send |

Every deployed agent carries exactly one base archetype tag. Departmental or role-specific customization layers on top as a harness profile, which is a named configuration set, not a new archetype.

---

## 3. Archetype detail

### 3.1 Research harness

**Purpose**
Agents that read, synthesize, and produce analyzed output grounded in provided sources. The most common archetype — covers every "go read X and tell me Y" pattern, plus deeper multi-source synthesis for analyst roles.

**Context construction**
Retrieval-heavy. The knowledge ingestion layer and any scoped document sets are the primary input channel. Context is assembled in a deterministic order — mandate summary, task description, retrieved sources with citations preserved, prior reasoning if multi-turn. External web content, if the agent has that tool access, is always passed through the injection scanner and is never merged into the system prompt layer.

**Reasoning scaffold**
Plan-then-research-then-synthesize-then-review. The harness requires the agent to produce an explicit research plan before retrieval, an explicit source list after retrieval, and an explicit claim-to-source mapping in the synthesis. Claims without source mappings are flagged by the evaluation hook before the output reaches the human.

**Tool binding**
Read-only access to the knowledge layer and approved external sources. No write tools by default. Citation-generation tools are required. Scratchpad-style tools (temporary working memory, structured outline generation) are encouraged.

**Enforcement hooks**
Injection scanner runs on every retrieved document before it enters context. Pre-execution ledger writes on every retrieval call with source identifier. Always-human guard evaluation is permissive here — most research actions do not hit always-human categories, but output publication does.

**Evaluation hooks**
Scored on: citation integrity (every claim maps to a retrieved source), fabrication rate (claims without sources flagged and counted), synthesis quality (domain rubric), retrieval recall (did the agent pull the obviously relevant sources). Evaluation outputs feed the per-agent baseline and the intelligence loop.

**Feedback ingestion**
Drift events from this archetype are heavily weighted toward fabrication detection. Human corrections on claim-to-source mapping feed directly into the harness tuning queue — if the same source-type-plus-claim pattern fails repeatedly across the fleet, the harness version gets a proposed update.

**Where it goes wrong**
Fabrication is the dominant failure mode. Over-broad retrieval that drowns the context in marginal sources is second. The evaluation hook is the primary defense — fabrication can't be prevented, but it can be caught before the human sees it.

---

### 3.2 Execution harness

**Purpose**
Agents that take short, decisive actions inside narrow tool sets. Procurement approval agents, incident response agents, data pipeline triggers, scheduled operators. The action set is small; the stakes per action are higher; the autonomy posture is tighter.

**Context construction**
Narrow. Mandate summary, task specification, current state of the system being acted on (pulled from the relevant integration), recent action history for pattern context. No open-ended retrieval. Context composition is deterministic and audited — deviation from the expected composition pattern is itself a drift signal.

**Reasoning scaffold**
Propose-then-verify-then-execute. The harness requires the agent to produce an explicit action proposal with parameters before any tool call, a verification pass that checks the proposal against mandate bounds, and only then the execution. Multi-step workflows are decomposed into discrete proposal-verify-execute cycles — no single tool call implicitly chains into the next.

**Tool binding**
Narrow, highly parameterized tool set. Every tool has mandate-derived parameter constraints enforced at the tool binding layer (not inside the agent's reasoning). An agent authorized to approve procurement up to $5,000 literally cannot submit a procurement call with a larger amount — the tool rejects it before the network call, same pattern as TransferGuard.

**Enforcement hooks**
Pre-execution ledger writes are mandatory on every tool call, not just consequential ones. Always-human guard evaluation is aggressive — the default for this archetype leans toward confirmation for anything near a category boundary. Trust score events fire on every successful and every blocked action.

**Evaluation hooks**
Scored on: mandate alignment (did the action fall cleanly within mandate intent), verification completeness (did the proposal-verify step catch the things it should have), action success rate, blocked-attempt rate. High blocked-attempt rate is a leading indicator of an agent probing its bounds.

**Feedback ingestion**
Drift events in this archetype are treated as first-class signals — execution agents don't have the noise floor that research agents do. Every major drift triggers review of whether the harness scaffold caught the issue appropriately. Mandate refinement proposals generated from this archetype are weighted higher in the human review queue.

**Where it goes wrong**
The loophole-hunting pattern — ten transactions of $999 instead of one of $10,000. The planning document already calls this out; the execution harness is where the defense actually lives. Aggregate and velocity checks have to exist at the tool binding layer, not just at the agent's reasoning layer, because a compromised or drifting agent cannot be trusted to respect limits that only exist in its prompt.

---

### 3.3 Orchestration harness

**Purpose**
Agents whose job is to coordinate other agents. The Technical Organizer and Strategic Organizer both use this archetype. Fleet-level routers, departmental coordinators, and any parent agent with spawning authority also live here.

**Context construction**
Fleet-aware. The orchestrator's context includes a live view of its direct children (status, current task, trust score), the structured communication channel with its peer organizer if applicable, pending work in the queue it manages, and the mandate that defines its coordination scope. No document retrieval beyond what's needed for coordination decisions.

**Reasoning scaffold**
Decompose-then-delegate-then-monitor. The harness requires explicit task decomposition before any delegation, explicit spawning or routing decisions with justification, and continuous monitoring of delegated work with defined escalation criteria. The scaffold explicitly forbids the orchestrator from executing downstream work itself — it decomposes and routes, it does not do.

**Tool binding**
Spawn, delegate, monitor, report. No direct implementation tools. This maps cleanly to the existing Orchestrator role in the RBAC matrix — can coordinate, cannot build. Spawning is gated by the pre-authorized classes defined in the orchestrator's mandate (per the planning doc's spawning governance). Structured inter-agent message tools are mandatory; freeform agent-to-agent communication is not available.

**Enforcement hooks**
Inter-agent identity verification (AgentShield Layer 4) is the critical hook — every message the orchestrator sends to a child or peer is cryptographically signed, every message it receives is verified. Pre-execution ledger writes on every spawn, delegation, and directive. Always-human guard evaluation is strict on anything that changes the shape of the fleet (out-of-class spawns, cross-department routing requests).

**Evaluation hooks**
Scored on: delegation appropriateness (did the right class of agent receive the right task), escalation latency (how quickly did the orchestrator surface issues upward), coordination overhead (fleet-wide time spent routing versus executing), children drift rate (are the orchestrator's children drifting more than baseline — if so, that's an orchestrator problem, not just a child problem).

**Feedback ingestion**
Organizer-class agents have stricter trust thresholds (Elevated Watch at 90, not 84). Their feedback loop is correspondingly more sensitive. Any meaningful pattern across the orchestrator's own behavior triggers a harness review at the CTO-plus-CEO signature level given the authority this archetype carries.

**Where it goes wrong**
The orchestrator that slowly takes on more work itself instead of delegating. The orchestrator that develops implicit routing biases that look innocuous individually but produce cross-department imbalance over time. Both are caught by the evaluation hook — coordination overhead and children drift rate are the two metrics that surface these patterns before they become structural.

---

### 3.4 Conversational harness

**Purpose**
Agents whose primary interface is a human. Helpdesk agents, onboarding assistants, knowledge-base front ends, clarification layers that sit in front of execution agents. The distinguishing feature is that the conversation itself is the work product, not a means to a tool call.

**Context construction**
Human-session aware. Context includes the conversation history for the current session, the user's role and scope (derived from authenticated identity, not from what the user says about themselves), any prior session state if the conversation is continuing, and relevant knowledge-layer content scoped to what the user is authorized to access. The user-identity-comes-from-authentication rule is a hard invariant — users cannot self-describe into elevated scope.

**Reasoning scaffold**
Clarify-then-respond. The default posture is to ask before acting. When a user request is ambiguous, the harness requires a clarification response, not a best-guess action. When a request falls outside scope, the harness requires explicit scope acknowledgment and either escalation or refusal — never silent narrowing of the request into something the agent can handle.

**Tool binding**
Information retrieval tools. Escalation and routing tools. No direct action tools by default — if the conversation leads to a required action, the conversational agent hands off to an execution-harness agent via the orchestration channel rather than acting itself. This separation is architectural: conversation and action are different archetypes, and combining them in one agent is the pattern that produces the highest-stakes drift events.

**Enforcement hooks**
Injection scanner on every user message. User-identity verification on every session. Pre-execution ledger write on every handoff to an execution agent, capturing the user context and the intent of the handoff. Always-human guard fires strictly on anything that would identify the agent as taking action on behalf of the user without an explicit handoff.

**Evaluation hooks**
Scored on: clarification appropriateness (did the agent ask when it should have), scope respect (did the agent stay within its bounds), handoff quality (when handing off, did it preserve enough context for the downstream agent), user satisfaction signal if available. Hallucination of capabilities or commitments is heavily penalized.

**Feedback ingestion**
Human corrections on specific conversation turns feed into a turn-level rubric that's easier to tune than whole-task rubrics. Patterns of repeated scope violations — the agent agreeing to do things it can't actually do — trigger harness tuning proposals focused on the clarify-then-respond scaffold.

**Where it goes wrong**
Scope creep. The agent that starts as an information provider and ends up making implicit commitments on behalf of the organization. The conversational archetype's hard separation from execution is the architectural defense — if the agent can't take the action itself, it can't accidentally commit to it.

---

### 3.5 Generative harness

**Purpose**
Agents that produce drafts, content, creative output. The Marketing view's content agents are the canonical example. Distinguishable from research by the expectation that the output is meant to persuade, engage, or represent the organization, not just to inform.

**Context construction**
Brand-aware. Context includes brand voice guidelines, style references, any content-specific inputs the user provides, and any audience context the content is targeting. Retrieval is narrower than research but deliberate — the harness pulls brand canon, not arbitrary sources.

**Reasoning scaffold**
Brief-then-draft-then-review. The harness requires the agent to produce an explicit brief derived from the request (what is this, who is it for, what does it need to accomplish) before drafting, and an explicit self-review pass against the brief before presenting. For regulated-industry generative use (healthcare content, financial content, legal content), the self-review pass includes domain-specific compliance checks.

**Tool binding**
Drafting, editing, and formatting tools. Content-management-system integration tools for the platforms the enterprise publishes to. The publication tools themselves are gated — drafting is autonomous, publication is always-human by default. This mirrors the conversational archetype's separation between talking and acting.

**Enforcement hooks**
Injection scanner on any external reference content the agent pulls in. Pre-execution ledger writes on every draft version the agent considers a candidate (not every intermediate token — the candidates the agent actually presents). Always-human guard fires on anything heading to a publication channel, anything using a named individual's identity externally, anything that crosses into compliance-sensitive domains.

**Evaluation hooks**
Scored on: brief adherence (did the output match the brief the agent itself produced), brand voice adherence (measured against canon references), factual grounding if the content makes factual claims (shared infrastructure with the research archetype's citation integrity hook), review pass quality (did the self-review catch issues the human then had to also catch — if so, the review pass is too lenient).

**Feedback ingestion**
Human edits on drafts are the richest feedback signal in this archetype. The diff between the agent's draft and the human-approved version, accumulated across deployments, produces highly specific harness tuning proposals — voice drift patterns, structural patterns, specific word-choice patterns. Unlike other archetypes, the tuning signal here is often at the prompt-scaffolding level rather than the structural level.

**Where it goes wrong**
Brand voice drift. Hallucinated statistics or claims presented with generative confidence. Commitment language that creates obligations the organization didn't intend. The always-human publication gate is the architectural defense — no generative agent ships output externally without a human signoff.

---

## 4. Harness evolution and governance

The planning doc already establishes that mandate changes require human sign-off and that critical rules are platform invariants. Harness evolution follows the same pattern, tiered by the scope of what's changing.

### Evolution flow

```
Observation — human, Red Team, or Technical Organizer identifies pattern
  → Proposal drafted — harness change request with evidence
    → Review queue — surfaces to appropriate human authority
      → Approval or rejection — signed, logged, reasoned
        → Version promotion — new signed harness version deployed
          → Rollout — existing agents migrated per policy
            → Observation — feedback loop continues
```

No step in this flow is autonomous. Proposals can be *generated* by observation, but every promotion requires human action.

### Change scope tiers

| Tier | Examples | Required signatories |
|---|---|---|
| **Tuning** | Context window size adjustments, retry policy, minor prompt-scaffold wording | Owning human |
| **Structural** | Adding or removing a reasoning pattern, changing an evaluation rubric, modifying tool binding parameter constraints | Department head + CTO |
| **Archetype-level** | Changes that affect the archetype's behavior across every deployment using it | CEO + CTO + CISO (multi-sig) |
| **Platform invariant** | Injection scanner hook, pre-execution ledger write, always-human guard integration, trust score event emission | **Not modifiable by the enterprise.** Changes require platform-level release. |

The platform-invariant tier is non-negotiable for the same reason the trust score's injection-attempt rule is non-negotiable — if it could be weakened by enterprise configuration, the CISO answer becomes "it depends" instead of "unconditionally."

### Versioning and rollback

Every harness version is:
- Cryptographically signed by the approving signatory or signatories
- Stored as an immutable artifact keyed by `archetype-version` (e.g., `research-v2.4.1`)
- Referenced by every agent running on it, so the ledger always answers "what harness version was this agent on when it took this action"
- Independently rollback-able, so a problematic promotion can be reversed without touching any other harness

Rollback is itself a promotion — it requires signatures, it's logged, it produces a new version number rather than pretending the intervening version didn't exist.

### The Technical Organizer's role in evolution

The Technical Organizer is the natural observer of cross-agent patterns that suggest harness tuning. Its position at the fleet monitoring level means it sees drift clusters, repeated human corrections, and performance trends that no individual human could track. The Organizer *generates* harness change proposals. It never promotes them.

A harness proposal from the Technical Organizer arrives in the review queue with full evidence — which agents, which patterns, which events, with what frequency. The human signatory sees the case and decides.

---

## 5. The model feedback loop in dedicated-infrastructure deployments

This is where dedicated compute — SLYD-contracted endpoints, on-prem deployments, reserved cluster capacity — becomes a platform differentiator rather than just an infrastructure choice.

### The separation of concerns

| Concern | Who controls | How it evolves |
|---|---|---|
| **Harness** | Enterprise Gamma platform, governed by the evolution flow in Section 4 | Proposal-and-approval, versioned, rollback-able |
| **Model** | The underlying inference provider (Neuraxis routing, enterprise dedicated endpoint, or enterprise-owned inference) | Separate pathway — fine-tuning, version pinning, or scheduled updates |

The harness stays stable while the model improves underneath it. The model can change providers entirely without the harness being aware. This separation is the architectural reason the platform can offer model-level improvement as a premium feature without destabilizing the governance layer.

### The feedback signal

The immutable ledger already contains the training signal. Every drift event, every Red Team finding, every human correction, every always-human confirmation, every trust score event, every successful task completion. For enterprises on dedicated infrastructure who opt into the feedback loop, ledger-derived behavioral data becomes input to a periodic fine-tuning pipeline running on their dedicated endpoint.

The model gets better at the enterprise's specific work patterns. Those improvements never leave the enterprise's infrastructure. Other enterprises do not benefit from or see this tuning — and that's the point.

### Opt-in governance

Fine-tuning pipeline opt-in is not a single switch. It is per-data-class:

- Task outcomes (success, failure, intermediate state) — typically approved
- Human correction diffs — typically approved with PII handling review
- Full conversation or document content — requires classification review, often restricted
- Identity-linked behavioral data — restricted by default, explicit approval required
- Anything touching legal privilege, attorney-client data, or privileged communications — never included

Classification happens at the ledger-write layer, not at the fine-tuning layer, because the wrong place to filter sensitive data is at the end of the pipeline.

### Model version governance

Model versions running in production get the same treatment as harness versions. Promotion requires signatures. The signatory tier depends on scope — routine tuning might need only the CTO; a new base model introduces enough behavioral change to warrant multi-sig.

### Regression detection

The same evaluation hooks that measure harness behavior measure model behavior. If a fine-tuned model produces more drift events than baseline, more fabrications than baseline, more always-human confirmations triggered than baseline — that's a regression. The feedback loop does not silently roll back, but it surfaces the regression as a high-priority review item. The CTO decides whether to revert, retune, or accept.

### Why this matters in the enterprise pitch

"Your models improve by operating in your environment, and those improvements never leave your infrastructure." That is a genuinely differentiated claim. Shared-endpoint providers cannot make it. It is the long-tail reason an enterprise stays on dedicated infrastructure once they start — the accumulated tuning is a switching cost that compounds.

It is also a natural fit for the SLYD Group business. The enterprise runs on dedicated compute contracted through SLYD. The tuning pipeline runs on that compute. The improvement stays on that compute. Every layer of the stack reinforces the same customer commitment.

---

## 6. Open questions

These are the places this document takes a position that should be stress-tested before the session spec gets written.

| # | Question | Current position | Needs |
|---|---|---|---|
| 1 | Is "archetype" the right primitive, or should harnesses be composed more granularly? | Five archetypes as base, profiles layer on top | Kyle review — does this match how the codebase actually wants to model it |
| 2 | Should the Technical Organizer's proposal-generation be in scope for v1, or is that v2? | Assumed v1 — but it's a real engineering effort | Kyle effort estimate |
| 3 | Does the harness version artifact live in the ledger itself or in a separate signed-artifact store? | Document implies ledger-referenced, not ledger-stored | Architecture call — ledger hygiene argues for separate store |
| 4 | How do harness version migrations handle in-flight agent work? | Implied "drain and migrate" — not specified | Needs operational design |
| 5 | Is the model feedback loop Standard Enterprise or a premium add-on? | Document positions it as premium, tied to dedicated infrastructure | Pricing conversation |
| 6 | For the generative archetype, how do we handle brand voice canon that doesn't yet exist in a formalized form? | Implied "ingest what exists and build from there" — hand-wavy | Discovery-phase question for the consultation agent |
| 7 | What's the relationship between harness version and agent card? | Agent card should reference harness version; not yet specified in planning doc | Additive update to the agent card schema |

---

*Document Status: Working Draft v1 — intended to ground the Session spec that follows*
*Next: Session spec slotting harness architecture into phase planning*
