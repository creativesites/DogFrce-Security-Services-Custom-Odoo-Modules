import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * `config` in env.ts is computed once, eagerly, at module-evaluation time
 * from `import.meta.env` (see env.ts's `readEnv`). To test different env
 * combinations we must reset the module registry and re-import between
 * cases, so each import sees a fresh evaluation of `readEnv` against the
 * env vars stubbed for that case — otherwise every test after the first
 * would just see whatever the first import captured.
 */
describe("config/env", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("defaults odooBaseUrl to localhost:8069 when unset", async () => {
    vi.stubEnv("VITE_ODOO_BASE_URL", "");
    const { config } = await import("./env");
    expect(config.odooBaseUrl).toBe("http://localhost:8069");
  });

  it("reads VITE_ODOO_BASE_URL when set", async () => {
    vi.stubEnv("VITE_ODOO_BASE_URL", "https://staging.example.com");
    const { config } = await import("./env");
    expect(config.odooBaseUrl).toBe("https://staging.example.com");
  });

  it("strips exactly one trailing slash from VITE_ODOO_BASE_URL", async () => {
    vi.stubEnv("VITE_ODOO_BASE_URL", "https://staging.example.com/");
    const { config } = await import("./env");
    expect(config.odooBaseUrl).toBe("https://staging.example.com");
  });

  it("defaults env to development when VITE_DEPLOYGUARD_ENV is unset", async () => {
    vi.stubEnv("VITE_DEPLOYGUARD_ENV", "");
    const { config } = await import("./env");
    expect(config.env).toBe("development");
  });

  it("reads VITE_DEPLOYGUARD_ENV when set to production", async () => {
    vi.stubEnv("VITE_DEPLOYGUARD_ENV", "production");
    const { config } = await import("./env");
    expect(config.env).toBe("production");
  });

  it("odooDb is null when VITE_ODOO_DB is unset", async () => {
    vi.stubEnv("VITE_ODOO_DB", "");
    const { config } = await import("./env");
    expect(config.odooDb).toBeNull();
  });

  it("odooDb reads VITE_ODOO_DB when set", async () => {
    vi.stubEnv("VITE_ODOO_DB", "dogforce-demo");
    const { config } = await import("./env");
    expect(config.odooDb).toBe("dogforce-demo");
  });

  it("platformApiBaseUrl is null when VITE_DEPLOYGUARD_API_BASE_URL is unset (MVP has no Platform API yet)", async () => {
    vi.stubEnv("VITE_DEPLOYGUARD_API_BASE_URL", "");
    const { config } = await import("./env");
    expect(config.platformApiBaseUrl).toBeNull();
  });

  it("appVersion defaults to 0.1.0-pilot when VITE_APP_VERSION is unset", async () => {
    vi.stubEnv("VITE_APP_VERSION", "");
    const { config } = await import("./env");
    expect(config.appVersion).toBe("0.1.0-pilot");
  });

  it("appVersion reads VITE_APP_VERSION when set (as CI's build step does)", async () => {
    vi.stubEnv("VITE_APP_VERSION", "0.1.0-pilot-abc1234");
    const { config } = await import("./env");
    expect(config.appVersion).toBe("0.1.0-pilot-abc1234");
  });

  it("isProduction() is true only when env is exactly 'production'", async () => {
    vi.stubEnv("VITE_DEPLOYGUARD_ENV", "production");
    const { isProduction } = await import("./env");
    expect(isProduction()).toBe(true);
  });

  it("isProduction() is false for development", async () => {
    vi.stubEnv("VITE_DEPLOYGUARD_ENV", "development");
    const { isProduction } = await import("./env");
    expect(isProduction()).toBe(false);
  });

  it("isProduction() is false for staging", async () => {
    vi.stubEnv("VITE_DEPLOYGUARD_ENV", "staging");
    const { isProduction } = await import("./env");
    expect(isProduction()).toBe(false);
  });
});
