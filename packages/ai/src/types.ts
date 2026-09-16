import type { ZodType } from "zod";

/**
 * A single fact the model was given as ground truth — a deterministic
 * value computed by a rule, never by the model itself. `validateOutput`
 * checks every numeric claim in an AI output against this set.
 * See DG-ADR-010 §1: "no invented numbers."
 */
export interface Fact {
  /** Stable id the output can reference, e.g. "coverage.current". */
  id: string;
  /** The deterministic value, as computed by a rule — not AI-derived. */
  value: number | string | boolean;
  /** Human-readable label, for error messages and audit display. */
  label: string;
}

/**
 * A piece of evidence the model was allowed to cite (an event, a
 * projection snapshot, a metric). An output citing an id not in this set
 * is rejected — see DG-ADR-010 §1: "no uncited claims."
 */
export interface EvidenceItem {
  id: string;
  kind: "event" | "projection" | "metric" | "feedback";
  /** Not sent to the model verbatim in every case, but always resolvable
   * by id — used only for audit display and validation error messages. */
  summary: string;
}

/** The controlled context a capability assembles before calling a provider. */
export interface ContextBundle {
  facts: Fact[];
  evidence: EvidenceItem[];
}

/** Every AI output must include citations — enforced by the schema each
 * capability declares, and re-checked by `validateOutput`. */
export interface CitedOutput {
  citations: string[];
}

export interface AIUsage {
  inputTokens: number;
  outputTokens: number;
  /** Cost in micro-units of the tenant's billing currency (avoids float
   * rounding on very small per-call costs). */
  costMicro: number;
}

export interface AIResult<T> {
  data: T;
  usage: AIUsage;
  /** Provider-assigned id for this specific call, for audit/support lookup. */
  providerRequestId: string;
  finishReason: "stop" | "length" | "safety" | "other";
}

export interface GenerateStructuredRequest<T> {
  /** Registered capability id + version, e.g. "adoption.drop.explain@1". */
  capability: string;
  model: string;
  system: string;
  input: ContextBundle;
  schema: ZodType<T>;
  temperature?: number;
  maxOutputTokens?: number;
}

/**
 * Provider-swappable AI abstraction (DG-ADR-010 §1). Feature code never
 * imports a provider SDK directly or names a model — it goes through
 * this interface, resolved from tenant/capability configuration.
 */
export interface AIProvider {
  readonly id: "gemini" | "openai" | "anthropic" | "local";
  generateStructured<T>(req: GenerateStructuredRequest<T>): Promise<AIResult<T>>;
  countTokens(req: { model: string; text: string }): Promise<number>;
}

export type Confidence = "low" | "medium" | "high";

export interface ValidationError {
  code: "uncited_evidence" | "unknown_fact" | "value_mismatch" | "missing_citations";
  message: string;
  /** The offending citation id or fact id, where applicable. */
  ref?: string;
}

export interface ValidationResult {
  ok: boolean;
  errors: ValidationError[];
}
