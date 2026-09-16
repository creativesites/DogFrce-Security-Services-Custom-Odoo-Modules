#!/usr/bin/env -S npx tsx
// One real, manually-run call against the live Gemini API — the only
// place in this package that ever touches the network. Not part of `npm
// test` (see README.md: the committed test suite never needs a key).
// Requires GEMINI_API_KEY in packages/ai/.env (gitignored, never commit
// the real key — see .env.example).
//
// Usage: npx tsx --env-file=.env scripts/smoke-test.ts

import { z } from "zod";
import { GeminiProvider, validateOutput } from "../src/index.js";

const apiKey = process.env.GEMINI_API_KEY;
if (!apiKey) {
  console.error("GEMINI_API_KEY not set. Run: npx tsx --env-file=.env scripts/smoke-test.ts");
  process.exit(1);
}

const provider = new GeminiProvider({ apiKey });

const schema = z.object({
  citations: z.array(z.string()),
  summary: z.string(),
});

const facts = [{ id: "coverage.delta", value: -8, label: "Coverage delta (points)" }];
const evidence = [
  { id: "event:0192f1a2", kind: "event" as const, summary: "Attendance batch missed for Site 12, Monday" },
];

console.log("Calling Gemini (gemini-3.6-flash) with structured output + citation instructions...\n");

const result = await provider.generateStructured({
  capability: "smoke-test@1",
  model: "gemini-3.6-flash",
  system:
    "You summarise operational facts for a security company manager in one sentence. " +
    "You may ONLY state numbers that appear in the `facts` you are given, and you MUST " +
    "cite every claim using ids from `evidence` in your `citations` array. If you cannot " +
    "support a claim with the given evidence, omit it rather than inventing detail.",
  input: { facts, evidence },
  schema,
});

console.log("Raw result:", JSON.stringify(result, null, 2));

const validation = validateOutput(result.data, {
  evidenceIds: evidence.map((e) => e.id),
  facts,
});

console.log("\nValidation:", validation.ok ? "PASSED" : "FAILED");
if (!validation.ok) {
  console.log(validation.errors);
  process.exit(1);
}

console.log("\n✅ Real Gemini call succeeded, structured output parsed, citations and numbers validated.");
