import { GoogleGenAI } from "@google/genai";
import type { ZodType } from "zod";
import type { AIProvider, AIResult, GenerateStructuredRequest } from "./types.js";

/**
 * The default AI provider (product decision R-4, 2026-09-16: "Gemini is
 * the default AI provider everywhere"). Uses Google's official
 * `@google/genai` SDK with structured (JSON-schema-constrained) output —
 * the model cannot return prose here, only a value matching the
 * capability's Zod schema, which `validateOutput` then re-checks against
 * the facts and evidence it was actually given.
 *
 * The underlying SDK client is injectable so tests never make a real
 * network call — see gemini.test.ts, which tests request *construction*
 * only.
 */
export interface GeminiClientLike {
  models: {
    generateContent(params: {
      model: string;
      contents: string;
      config?: {
        systemInstruction?: string;
        responseMimeType?: string;
        responseSchema?: unknown;
        temperature?: number;
        maxOutputTokens?: number;
      };
    }): Promise<{
      text?: string;
      usageMetadata?: { promptTokenCount?: number; candidatesTokenCount?: number };
      candidates?: { finishReason?: string }[];
      responseId?: string;
    }>;
  };
}

export interface GeminiProviderOptions {
  apiKey: string;
  /** Injectable for tests; defaults to a real `GoogleGenAI` client. */
  client?: GeminiClientLike;
  /** USD micro-cents per 1K input/output tokens, for cost tracking. Real
   * pricing varies by model and should come from tenant/model config in
   * V1 — these are placeholder defaults so `usage.costMicro` is never
   * silently wrong-shaped. */
  pricePerKTokenMicro?: { input: number; output: number };
}

const FINISH_REASON_MAP: Record<string, AIResult<unknown>["finishReason"]> = {
  STOP: "stop",
  MAX_TOKENS: "length",
  SAFETY: "safety",
  RECITATION: "safety",
};

export class GeminiProvider implements AIProvider {
  readonly id = "gemini" as const;
  private readonly client: GeminiClientLike;
  private readonly pricePerKTokenMicro: { input: number; output: number };

  constructor(options: GeminiProviderOptions) {
    this.client = options.client ?? (new GoogleGenAI({ apiKey: options.apiKey }) as unknown as GeminiClientLike);
    this.pricePerKTokenMicro = options.pricePerKTokenMicro ?? { input: 0, output: 0 };
  }

  async generateStructured<T>(req: GenerateStructuredRequest<T>): Promise<AIResult<T>> {
    const responseSchema = zodToGeminiSchema(req.schema);

    const response = await this.client.models.generateContent({
      model: req.model,
      contents: renderContext(req.input),
      config: {
        systemInstruction: req.system,
        responseMimeType: "application/json",
        responseSchema,
        temperature: req.temperature,
        maxOutputTokens: req.maxOutputTokens,
      },
    });

    if (!response.text) {
      throw new Error(`Gemini returned no text for capability "${req.capability}".`);
    }

    let parsedJson: unknown;
    try {
      parsedJson = JSON.parse(response.text);
    } catch {
      throw new Error(`Gemini response for "${req.capability}" was not valid JSON.`);
    }

    const parsed = req.schema.safeParse(parsedJson);
    if (!parsed.success) {
      throw new Error(
        `Gemini response for "${req.capability}" did not match its schema: ${parsed.error.message}`,
      );
    }

    const inputTokens = response.usageMetadata?.promptTokenCount ?? 0;
    const outputTokens = response.usageMetadata?.candidatesTokenCount ?? 0;
    const rawFinish = response.candidates?.[0]?.finishReason ?? "STOP";

    return {
      data: parsed.data,
      usage: {
        inputTokens,
        outputTokens,
        costMicro: Math.round(
          (inputTokens / 1000) * this.pricePerKTokenMicro.input +
            (outputTokens / 1000) * this.pricePerKTokenMicro.output,
        ),
      },
      providerRequestId: response.responseId ?? "unknown",
      finishReason: FINISH_REASON_MAP[rawFinish] ?? "other",
    };
  }

  async countTokens(req: { model: string; text: string }): Promise<number> {
    // Placeholder heuristic (≈4 chars/token) until wired to the SDK's real
    // countTokens endpoint — good enough for local budget estimates, not
    // for billing. Flagged clearly so it's never mistaken for exact.
    return Math.ceil(req.text.length / 4);
  }
}

function renderContext(input: GenerateStructuredRequest<unknown>["input"]): string {
  return JSON.stringify({ facts: input.facts, evidence: input.evidence });
}

/**
 * Minimal Zod → Gemini responseSchema converter, covering exactly the
 * shapes DG-ADR-010-style capability schemas need (object/array/string/
 * number/boolean/enum). Not a general-purpose Zod introspector — extend
 * deliberately, don't generalize speculatively.
 */
function zodToGeminiSchema(schema: ZodType): unknown {
  // Zod's internal `_def` shape is what every schema-to-X converter in the
  // ecosystem relies on; there is no public "toJsonSchema" on the base
  // ZodType as of the pinned version, so this reaches into `_def`
  // deliberately, one case at a time.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const def = (schema as any)._def;
  const typeName = def?.typeName;

  switch (typeName) {
    case "ZodObject": {
      const shape = def.shape();
      const properties: Record<string, unknown> = {};
      const required: string[] = [];
      for (const [key, value] of Object.entries(shape)) {
        properties[key] = zodToGeminiSchema(value as ZodType);
        if (!isOptional(value as ZodType)) required.push(key);
      }
      return { type: "OBJECT", properties, required };
    }
    case "ZodArray":
      return { type: "ARRAY", items: zodToGeminiSchema(def.type) };
    case "ZodString":
      return { type: "STRING" };
    case "ZodNumber":
      return { type: "NUMBER" };
    case "ZodBoolean":
      return { type: "BOOLEAN" };
    case "ZodEnum":
      return { type: "STRING", enum: def.values };
    case "ZodOptional":
    case "ZodNullable":
      return zodToGeminiSchema(def.innerType);
    case "ZodDefault":
      return zodToGeminiSchema(def.innerType);
    default:
      throw new Error(`zodToGeminiSchema: unsupported Zod type "${typeName}" — extend deliberately.`);
  }
}

function isOptional(schema: ZodType): boolean {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const typeName = (schema as any)._def?.typeName;
  return typeName === "ZodOptional" || typeName === "ZodDefault";
}
