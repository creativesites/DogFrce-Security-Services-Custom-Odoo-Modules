import type { CitedOutput, Fact, ValidationError, ValidationResult } from "./types.js";

/**
 * The safety-critical function in this package. Implements DG-ADR-010's
 * two hard rules for every AI output:
 *
 *   1. "No uncited claims" — every entry in `citations` must reference an
 *      evidence id the model was actually given. An empty citations array
 *      is also rejected: a capability with nothing to point to should not
 *      produce output at all (see 11-ai-intelligence.md §5, "refusal is
 *      valid").
 *   2. "No invented numbers" — every numeric value anywhere in the output
 *      must match a fact's value the model was given as ground truth. This
 *      is a conservative, whole-object scan: it walks the output looking
 *      for any `number`, and flags one that doesn't equal any known fact
 *      (within floating-point tolerance). That's deliberately strict — a
 *      false positive (a harmless number gets flagged) means a human
 *      reviews an output that was actually fine; a false negative (a
 *      fabricated number slips through) means a manager acts on a number
 *      nobody computed. We accept the former risk, never the latter.
 *
 * A rejected output is never shown to a user — see the pipeline in
 * 11-ai-intelligence.md §2 ("REJECT, log, retry once, then fail closed").
 */
export function validateOutput(
  output: unknown,
  context: { evidenceIds: string[]; facts: Fact[] },
): ValidationResult {
  const errors: ValidationError[] = [];

  const citations = extractCitations(output);
  if (citations === null) {
    errors.push({
      code: "missing_citations",
      message: "Output has no `citations` field, or it is not an array of strings.",
    });
  } else if (citations.length === 0) {
    errors.push({
      code: "missing_citations",
      message: "Output has an empty citations array — a claim with no evidence should not be produced.",
    });
  } else {
    const allowed = new Set(context.evidenceIds);
    for (const id of citations) {
      if (!allowed.has(id)) {
        errors.push({
          code: "uncited_evidence",
          message: `Output cites evidence id "${id}", which was not in the context it was given.`,
          ref: id,
        });
      }
    }
  }

  const knownNumbers = knownFactValues(context.facts);
  const foundNumbers = collectNumbers(output, "citations");
  for (const { value, path } of foundNumbers) {
    if (!numberMatchesAny(value, knownNumbers)) {
      errors.push({
        code: "value_mismatch",
        message: `Output contains the number ${value} at "${path}", which does not match any fact it was given.`,
        ref: path,
      });
    }
  }

  return { ok: errors.length === 0, errors };
}

function extractCitations(output: unknown): string[] | null {
  if (
    typeof output !== "object" ||
    output === null ||
    !("citations" in output) ||
    !Array.isArray((output as CitedOutput).citations) ||
    !(output as CitedOutput).citations.every((c) => typeof c === "string")
  ) {
    return null;
  }
  return (output as CitedOutput).citations;
}

function knownFactValues(facts: Fact[]): number[] {
  return facts
    .map((f) => f.value)
    .filter((v): v is number => typeof v === "number");
}

const FLOAT_TOLERANCE = 1e-9;

function numberMatchesAny(value: number, known: number[]): boolean {
  return known.some((k) => Math.abs(k - value) <= FLOAT_TOLERANCE);
}

/** Walks an arbitrary JSON-like value and collects every `number` found,
 * with a dotted path for error messages. Skips the given top-level key
 * (citations are strings anyway, but this keeps the walk's intent clear). */
function collectNumbers(value: unknown, skipKey: string, path = "$"): { value: number; path: string }[] {
  const results: { value: number; path: string }[] = [];

  function walk(v: unknown, p: string) {
    if (typeof v === "number" && Number.isFinite(v)) {
      results.push({ value: v, path: p });
      return;
    }
    if (Array.isArray(v)) {
      v.forEach((item, i) => walk(item, `${p}[${i}]`));
      return;
    }
    if (v !== null && typeof v === "object") {
      for (const [key, val] of Object.entries(v)) {
        if (p === "$" && key === skipKey) continue;
        walk(val, `${p}.${key}`);
      }
    }
  }

  walk(value, path);
  return results;
}
