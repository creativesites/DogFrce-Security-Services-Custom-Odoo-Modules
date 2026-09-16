/**
 * Deployment configuration boundary.
 *
 * MVP DEVIATION from docs/deployguard/19-backend-architecture.md: there is no
 * DeployGuard Platform API yet (BUILD-ORDER P1 hasn't shipped). This desktop
 * build therefore talks to DeployGuard ERP (Odoo) directly for authentication
 * and everything else. See desktop/DEVIATIONS.md for the full rationale and
 * the migration path back to the planned architecture.
 *
 * Nothing sensitive lives here — only non-secret endpoint configuration,
 * read from Vite env vars (see .env.example). Never hardcode a URL in a
 * component; always import from here so the future Platform API swap is a
 * one-file change.
 */

export type DeploymentEnv = "development" | "staging" | "production";

export interface AppConfig {
  env: DeploymentEnv;
  odooBaseUrl: string;
  odooDb: string | null;
  /** Unset in the MVP vertical slice — reserved for BUILD-ORDER P1+. */
  platformApiBaseUrl: string | null;
  appVersion: string;
}

function readEnv(key: string, fallback = ""): string {
  const v = (import.meta.env as Record<string, string | undefined>)[key];
  return v && v.length > 0 ? v : fallback;
}

export const config: AppConfig = {
  env: (readEnv("VITE_DEPLOYGUARD_ENV", "development") as DeploymentEnv) ?? "development",
  odooBaseUrl: readEnv("VITE_ODOO_BASE_URL", "http://localhost:8069").replace(/\/$/, ""),
  odooDb: readEnv("VITE_ODOO_DB") || null,
  platformApiBaseUrl: readEnv("VITE_DEPLOYGUARD_API_BASE_URL") || null,
  appVersion: readEnv("VITE_APP_VERSION", "0.1.0-pilot"),
};

export function isProduction(): boolean {
  return config.env === "production";
}
