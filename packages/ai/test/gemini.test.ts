import { describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { GeminiProvider, type GeminiClientLike } from "../src/gemini.js";

/**
 * Tests request *construction* and response *parsing* against a fake
 * client — never a real network call, so this suite needs no API key and
 * never touches the real Gemini API. See scripts/smoke-test.ts for the
 * one real, manually-run call that proves the class works end-to-end
 * (already run once against the live API — see git history for the
 * verified output).
 */
function fakeClient(responseText: string, overrides: Partial<Awaited<ReturnType<GeminiClientLike["models"]["generateContent"]>>> = {}) {
  const generateContent = vi.fn().mockResolvedValue({
    text: responseText,
    usageMetadata: { promptTokenCount: 100, candidatesTokenCount: 20 },
    candidates: [{ finishReason: "STOP" }],
    responseId: "fake-request-id",
    ...overrides,
  });
  return { client: { models: { generateContent } }, generateContent };
}

const schema = z.object({
  citations: z.array(z.string()),
  summary: z.string(),
  delta: z.number(),
});

describe("GeminiProvider.generateStructured", () => {
  it("sends the capability's model, system prompt, and context as the request", async () => {
    const { client, generateContent } = fakeClient(
      JSON.stringify({ citations: ["event:1"], summary: "ok", delta: -8 }),
    );
    const provider = new GeminiProvider({ apiKey: "unused-fake-key", client });

    await provider.generateStructured({
      capability: "adoption.drop.explain@1",
      model: "gemini-3.6-flash",
      system: "You are a careful operational analyst.",
      input: {
        facts: [{ id: "coverage.delta", value: -8, label: "Coverage delta" }],
        evidence: [{ id: "event:1", kind: "event", summary: "…" }],
      },
      schema,
    });

    expect(generateContent).toHaveBeenCalledTimes(1);
    const call = generateContent.mock.calls[0][0];
    expect(call.model).toBe("gemini-3.6-flash");
    expect(call.config.systemInstruction).toBe("You are a careful operational analyst.");
    expect(call.config.responseMimeType).toBe("application/json");
    expect(JSON.parse(call.contents)).toEqual({
      facts: [{ id: "coverage.delta", value: -8, label: "Coverage delta" }],
      evidence: [{ id: "event:1", kind: "event", summary: "…" }],
    });
  });

  it("parses a valid JSON response matching the schema", async () => {
    const { client } = fakeClient(JSON.stringify({ citations: ["event:1"], summary: "ok", delta: -8 }));
    const provider = new GeminiProvider({ apiKey: "unused-fake-key", client });

    const result = await provider.generateStructured({
      capability: "adoption.drop.explain@1",
      model: "gemini-3.6-flash",
      system: "sys",
      input: { facts: [], evidence: [] },
      schema,
    });

    expect(result.data).toEqual({ citations: ["event:1"], summary: "ok", delta: -8 });
    expect(result.usage).toEqual({ inputTokens: 100, outputTokens: 20, costMicro: 0 });
    expect(result.providerRequestId).toBe("fake-request-id");
    expect(result.finishReason).toBe("stop");
  });

  it("throws if the response text is not valid JSON", async () => {
    const { client } = fakeClient("not json at all");
    const provider = new GeminiProvider({ apiKey: "unused-fake-key", client });

    await expect(
      provider.generateStructured({
        capability: "adoption.drop.explain@1",
        model: "gemini-3.6-flash",
        system: "sys",
        input: { facts: [], evidence: [] },
        schema,
      }),
    ).rejects.toThrow(/not valid JSON/);
  });

  it("throws if the JSON response doesn't match the schema", async () => {
    const { client } = fakeClient(JSON.stringify({ wrong: "shape" }));
    const provider = new GeminiProvider({ apiKey: "unused-fake-key", client });

    await expect(
      provider.generateStructured({
        capability: "adoption.drop.explain@1",
        model: "gemini-3.6-flash",
        system: "sys",
        input: { facts: [], evidence: [] },
        schema,
      }),
    ).rejects.toThrow(/did not match its schema/);
  });

  it("maps MAX_TOKENS finish reason to 'length'", async () => {
    const { client } = fakeClient(
      JSON.stringify({ citations: ["event:1"], summary: "ok", delta: -8 }),
      { candidates: [{ finishReason: "MAX_TOKENS" }] },
    );
    const provider = new GeminiProvider({ apiKey: "unused-fake-key", client });

    const result = await provider.generateStructured({
      capability: "adoption.drop.explain@1",
      model: "gemini-3.6-flash",
      system: "sys",
      input: { facts: [], evidence: [] },
      schema,
    });

    expect(result.finishReason).toBe("length");
  });

  it("computes cost from configured per-1K-token pricing", async () => {
    const { client } = fakeClient(JSON.stringify({ citations: ["event:1"], summary: "ok", delta: -8 }), {
      usageMetadata: { promptTokenCount: 2000, candidatesTokenCount: 500 },
    });
    const provider = new GeminiProvider({
      apiKey: "unused-fake-key",
      client,
      pricePerKTokenMicro: { input: 100, output: 400 },
    });

    const result = await provider.generateStructured({
      capability: "adoption.drop.explain@1",
      model: "gemini-3.6-flash",
      system: "sys",
      input: { facts: [], evidence: [] },
      schema,
    });

    // 2000/1000 * 100 + 500/1000 * 400 = 200 + 200 = 400
    expect(result.usage.costMicro).toBe(400);
  });
});
