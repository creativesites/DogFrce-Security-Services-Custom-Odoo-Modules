import { describe, expect, it } from "vitest";
import { validateOutput } from "../src/validate.js";
import type { Fact } from "../src/types.js";

const facts: Fact[] = [
  { id: "coverage.current", value: 64, label: "Current coverage" },
  { id: "coverage.previous", value: 72, label: "Previous coverage" },
  { id: "coverage.delta", value: -8, label: "Coverage delta" },
  { id: "confidence.sample_size", value: 38, label: "Sample size" },
];

const evidenceIds = ["event:0192f1a2", "event:0192f3be", "snapshot:0192f3bf"];

describe("validateOutput", () => {
  it("accepts an output that cites known evidence and states only known numbers", () => {
    const output = {
      citations: ["event:0192f1a2", "snapshot:0192f3bf"],
      summary: "Coverage dropped from 72 to 64 (-8 points) across 38 samples.",
      from: 72,
      to: 64,
      delta: -8,
    };
    const result = validateOutput(output, { evidenceIds, facts });
    expect(result.ok).toBe(true);
    expect(result.errors).toEqual([]);
  });

  it("rejects an output with no citations field", () => {
    const output = { summary: "Coverage dropped." };
    const result = validateOutput(output, { evidenceIds, facts });
    expect(result.ok).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({ code: "missing_citations" }),
    );
  });

  it("rejects an output with an empty citations array", () => {
    const output = { citations: [], summary: "Coverage dropped." };
    const result = validateOutput(output, { evidenceIds, facts });
    expect(result.ok).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({ code: "missing_citations" }),
    );
  });

  it("rejects a citation for an evidence id not in the allowed set", () => {
    const output = { citations: ["event:not-real"], summary: "x" };
    const result = validateOutput(output, { evidenceIds, facts });
    expect(result.ok).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({ code: "uncited_evidence", ref: "event:not-real" }),
    );
  });

  it("rejects a fabricated number not present in the facts", () => {
    const output = { citations: ["event:0192f1a2"], summary: "x", to: 999 };
    const result = validateOutput(output, { evidenceIds, facts });
    expect(result.ok).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({ code: "value_mismatch" }),
    );
  });

  it("checks numbers nested inside objects and arrays", () => {
    const output = {
      citations: ["event:0192f1a2"],
      breakdown: [{ label: "a", delta: -8 }, { label: "b", delta: 999 }],
    };
    const result = validateOutput(output, { evidenceIds, facts });
    expect(result.ok).toBe(false);
    const mismatch = result.errors.find((e) => e.code === "value_mismatch");
    expect(mismatch?.ref).toBe("$.breakdown[1].delta");
  });

  it("does not flag numbers embedded in strings", () => {
    const output = {
      citations: ["event:0192f1a2"],
      summary: "Coverage is at 999% in this made-up sentence but it's just text",
    };
    const result = validateOutput(output, { evidenceIds, facts });
    expect(result.ok).toBe(true);
  });

  it("does not flag booleans as numbers", () => {
    const output = { citations: ["event:0192f1a2"], flagged: true };
    const result = validateOutput(output, { evidenceIds, facts });
    expect(result.ok).toBe(true);
  });

  it("matches floating-point fact values within tolerance", () => {
    const floatFacts: Fact[] = [{ id: "rate", value: 0.1 + 0.2, label: "Rate" }];
    const output = { citations: ["event:0192f1a2"], rate: 0.3 };
    const result = validateOutput(output, { evidenceIds, facts: floatFacts });
    expect(result.ok).toBe(true);
  });

  it("rejects when citations is present but not an array of strings", () => {
    const output = { citations: "event:0192f1a2" };
    const result = validateOutput(output, { evidenceIds, facts });
    expect(result.ok).toBe(false);
    expect(result.errors).toContainEqual(
      expect.objectContaining({ code: "missing_citations" }),
    );
  });

  it("collects multiple distinct errors in one pass rather than stopping at the first", () => {
    const output = {
      citations: ["event:not-real-1", "event:not-real-2"],
      value: 12345,
    };
    const result = validateOutput(output, { evidenceIds, facts });
    expect(result.errors.length).toBeGreaterThanOrEqual(3);
  });
});
