# @deployguard/ai

**Status: infrastructure, not a feature.** Nothing in this package is
wired into any UI yet, and it should not be presented as an MVP
capability — see
[`docs/deployguard/28-mvp-scope.md`](../../docs/deployguard/28-mvp-scope.md)
§3.1. MVP ships zero AI-generated text. This package exists so that V1
("AI comes after the pilot" —
[`docs/deployguard/29-roadmap.md`](../../docs/deployguard/29-roadmap.md)
§3) isn't a cold start: the provider abstraction, the Gemini
implementation, and — most importantly — the **output validator** that
makes AI outputs trustworthy are built and tested now, against fixture
data, ahead of there being any real operational data to reason over.

It implements [DG-ADR-010](../../docs/deployguard/adr/DG-ADR-010-ai-architecture.md).

## What's here

| File | Purpose |
|---|---|
| `src/types.ts` | `AIProvider` interface, `AIResult`, `CapabilityManifest`, `Citation`/`EvidenceItem` shapes |
| `src/validate.ts` | **The safety-critical part.** Rejects any AI output that cites evidence not present in its context, or states a number that doesn't match the deterministic facts it was given. Fully testable without any API key — this is what "no invented numbers, no uncited claims" (DG-ADR-010 §3) actually means in code. |
| `src/gemini.ts` | `AIProvider` implementation using Google's official `@google/genai` SDK. Structured output via a JSON schema per capability. |
| `src/index.ts` | Public exports |

## What's deliberately NOT here yet

- No capability registry wiring to real data (adoption, exceptions —
  none of that exists yet; see BUILD-ORDER P5/P6).
- No context assembler pulling from a real backend (there is no
  DeployGuard Platform backend yet — see `desktop/DEVIATIONS.md` D-1).
- No UI. The desktop app's "Coming soon" tiles stay honest placeholders
  until there's something real to show.
- No live calls in tests. `gemini.test.ts` tests request *construction*
  against a fake client, never hits the real API — no key is required to
  run this package's test suite.

## Running tests

```bash
cd packages/ai
npm install
npm test
```

## Using it (once there's something real to call it with)

```ts
import { GeminiProvider, validateOutput } from "@deployguard/ai";

const provider = new GeminiProvider({ apiKey: process.env.GEMINI_API_KEY! });

const result = await provider.generateStructured({
  capability: "adoption.drop.explain",
  model: "gemini-3.6-flash",
  system: promptTemplate,
  input: contextBundle,       // built by a context assembler that doesn't exist yet
  schema: adoptionExplanationSchema,
});

const validation = validateOutput(result.data, {
  evidenceIds: contextBundle.evidenceIds,  // every id the model was allowed to cite
  facts: contextBundle.facts,               // every number the model was given
});

if (!validation.ok) {
  // reject: uncited claim or invented number — see validation.errors
}
```
