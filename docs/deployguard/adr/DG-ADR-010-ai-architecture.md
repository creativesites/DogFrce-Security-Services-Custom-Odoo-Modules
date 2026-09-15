# DG-ADR-010 — AI Architecture

- **Status:** Proposed (default-provider choice Accepted by product decision R-4)
- **Date:** 2026-09-15
- **Related:** [11-ai-intelligence](../11-ai-intelligence.md), [DG-ADR-009](DG-ADR-009-event-architecture.md), [23-audit-system](../23-audit-system.md)

## Context

The Platform uses AI as an **intelligence layer**, not a chatbot:

- summarise operational state with citations;
- classify feedback;
- interpret adoption drops;
- prioritise the inbox;
- assist support;
- (V2) draft training content.

Deterministic facts (is a task overdue, is a shift uncovered) are computed by rules, never by a model. AI outputs affecting people must be reviewable, evidenced and approved before action.

**Gemini is the default provider** (R-4). The architecture must allow OpenAI, Anthropic or local models without rewrites.

DeployGuard ERP already contains `security_ai_engine`:

- multi-provider;
- currently defaulting to Claude (defect D-1, to be switched to Gemini);
- confirm-before-write tool loop;
- `security.ai.log`.

It serves in-Odoo features. The Platform must not depend on it (OQ-3).

## Decision

### 1. Provider abstraction (`packages/ai`)

```ts
interface AIProvider {
  id: 'gemini' | 'openai' | 'anthropic' | 'local';
  generateStructured<T>(req: {
    capability: CapabilityId;
    model: ModelRef;               // resolved from tenant/capability config, never hardcoded
    system: string;                // versioned prompt template output
    input: ContextBundle;          // assembled, redacted, token-budgeted
    schema: ZodSchema<T>;          // output contract
    temperature?: number;
    maxOutputTokens?: number;
  }): Promise<AIResult<T>>;        // parsed output + usage + finishReason + providerRequestId
  generateText(req: …): Promise<AIResult<string>>;
  embed(req: { texts: string[]; model: ModelRef }): Promise<number[][]>;
  countTokens(req: …): Promise<number>;
}
```

- **Gemini provider:** implemented with Google's official Gen AI SDK for JavaScript, using structured output (response schema) and paid-tier API terms (OQ-15).
- **Model selection:** per capability through a platform `ai_model_catalog` plus a tenant override. Example tiers:
  - fast/cheap model for classification;
  - higher-reasoning model for briefs.

  **No model name appears in feature code.**
- **Fallback:** an optional secondary provider per capability. It is used only for transient provider failures, never to dodge a policy refusal.

### 2. Capability registry

Every AI use is a registered **capability** with a manifest:

| Field | Purpose |
|---|---|
| `id`, `version` | e.g. `brief.weekly@2` |
| `riskTier` | `informational` (summaries) · `draft` (content needing review) · `proposal` (suggests an action) |
| `trigger` | Event, schedule or user request |
| `contextSources` | Allowlist of context providers (e.g. `exceptions.openSummary`, `adoption.snapshotDeltas`, `knowledge.search`) |
| `redaction` | Fields removed or pseudonymised before sending (e.g. national ID, phone, home address, free-text health notes) |
| `outputSchema` | Zod schema, including a mandatory `citations[]` of evidence IDs |
| `promptTemplate` | Versioned file; changes require an eval run |
| `evalSet` | Fixture cases with expected properties |
| `approval` | Who must approve before any effect (roles) |
| `budget` | Max tokens and cost per run; tenant monthly cap |

### 3. Pipeline

```
TRIGGER → DETERMINISTIC FACTS (rules/metrics) → CONTEXT ASSEMBLER (allowlist, scope, redaction, budget)
→ PROVIDER → OUTPUT VALIDATION (schema; every citation ∈ supplied evidence IDs; no new numbers
   unless present in facts) → POLICY GUARD (riskTier → approval requirement) → STORE (ai_run,
   ai_insight / ai_recommendation as draft|proposed) → HUMAN ACTION (approve/edit/dismiss)
→ EFFECT via normal module commands (audited) → FEEDBACK (accepted/rejected ratings feed evals)
```

- **Citation integrity:** outputs citing IDs not present in the context bundle are rejected. Quantitative claims must match deterministic facts in the bundle, or the output is marked invalid.
- **Confidence:** computed from evidence (data sufficiency, rule agreement, recency), not model self-reported confidence. The model's stated uncertainty is recorded but not used alone.
- **Hard limits:** AI has no tools that mutate data. "Proposals" are records a human converts into commands. The AI cannot discipline, terminate, edit HR records, change security policy, or alter Odoo financial data (brief §24).

### 4. Retrieval

- **Knowledge-base retrieval:** PostgreSQL full-text search in MVP. **pgvector** embeddings in V1 for semantic search over approved knowledge articles and course content only.
- **Operational data** is never embedded wholesale. It enters context through typed context providers.

### 5. Observability & audit

`ai_run` records:

- capability and version, provider, model;
- prompt template hash;
- context bundle reference (stored encrypted, retention per OQ-14);
- output;
- validation result;
- tokens, cost, latency;
- approver actions.

AI spend dashboards are available per tenant and per capability.

### 6. Relationship to `security_ai_engine`

- It stays in DeployGuard ERP for in-Odoo features and switches its default to Gemini (Stage 0).
- The Platform does not call it.
- Convergence, e.g. Odoo using Platform capabilities through the bridge, is evaluated in V1 (OQ-3).

## Alternatives

| Option | Why not |
|---|---|
| Hard-code the Gemini SDK in feature modules | Violates provider independence; model and prompt changes scatter through code. |
| LangChain / heavy agent frameworks | Abstraction churn, opaque prompts, harder auditing; our needs are structured single-shot calls with controlled context. |
| Autonomous agents with tool access to the ERP | Conflicts with the human-in-the-loop requirement and auditability. |
| Route Platform AI through Odoo `security_ai_engine` | Couples Platform intelligence to each tenant's ERP, one database per tenant; no cross-module Platform context. |
| Fine-tuned custom models | Premature; no labelled data yet. Revisit with accumulated approved outputs. |

## Tradeoffs

| We gain | We accept |
|---|---|
| Provider-swappable, auditable, testable AI | Upfront work: registry, validators, eval harness |
| Evidence-grounded outputs management can trust | Some valid model insights are rejected for lacking citations (by design) |
| Cost control per tenant/capability | Latency of validation and retries |

## Consequences

- **MVP:** ships the interface, Gemini provider, `ai_run` table and eval harness skeleton, with no user-facing AI (P9 delivers V1 capabilities).
- **Privacy:** before any capability processes personal data, OQ-6 and OQ-15 must be resolved.
- **Prompt changes:** a PR touching a prompt template runs its eval set in CI; regressions block the merge.
