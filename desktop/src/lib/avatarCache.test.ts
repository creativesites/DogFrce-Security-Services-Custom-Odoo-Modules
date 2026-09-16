import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearCachedAvatar, getCachedAvatar, setCachedAvatar } from "./avatarCache";

/**
 * This project has no DOM test environment configured (vitest defaults to
 * "node"), so `window` doesn't exist at test time. Rather than pull in
 * jsdom/happy-dom for one small module, this stubs a minimal
 * Map-backed `window.localStorage` — enough to exercise the real
 * get/set/clear/throw behavior in avatarCache.ts without a new dependency.
 */
function installFakeLocalStorage() {
  const store = new Map<string, string>();
  const localStorage = {
    getItem: vi.fn((key: string) => store.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => { store.set(key, value); }),
    removeItem: vi.fn((key: string) => { store.delete(key); }),
  };
  vi.stubGlobal("window", { localStorage });
  return localStorage;
}

describe("avatarCache", () => {
  let localStorage: ReturnType<typeof installFakeLocalStorage>;

  beforeEach(() => {
    localStorage = installFakeLocalStorage();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns null when nothing is cached", () => {
    expect(getCachedAvatar(7)).toBeNull();
  });

  it("round-trips a cached value", () => {
    setCachedAvatar(7, "data:image/png;base64,AAAA");
    expect(getCachedAvatar(7)).toBe("data:image/png;base64,AAAA");
  });

  it("keys the cache per uid", () => {
    setCachedAvatar(1, "data:image/png;base64,ONE");
    setCachedAvatar(2, "data:image/png;base64,TWO");
    expect(getCachedAvatar(1)).toBe("data:image/png;base64,ONE");
    expect(getCachedAvatar(2)).toBe("data:image/png;base64,TWO");
  });

  it("clears a cached value", () => {
    setCachedAvatar(7, "data:image/png;base64,AAAA");
    clearCachedAvatar(7);
    expect(getCachedAvatar(7)).toBeNull();
  });

  it("degrades to null instead of throwing when localStorage.getItem throws", () => {
    localStorage.getItem.mockImplementation(() => { throw new Error("blocked"); });
    expect(getCachedAvatar(7)).toBeNull();
  });

  it("does not throw when localStorage.setItem throws", () => {
    localStorage.setItem.mockImplementation(() => { throw new Error("quota exceeded"); });
    expect(() => setCachedAvatar(7, "data:image/png;base64,AAAA")).not.toThrow();
  });

  it("does not throw when localStorage.removeItem throws", () => {
    localStorage.removeItem.mockImplementation(() => { throw new Error("blocked"); });
    expect(() => clearCachedAvatar(7)).not.toThrow();
  });
});
