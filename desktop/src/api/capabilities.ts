import { callKw } from "./odoo";

/**
 * True when a call failed because the Odoo module behind it isn't installed
 * on this server. src-tauri/src/odoo.rs turns Odoo 19's werkzeug NotFound
 * (a missing model) into `module_not_installed`; older servers raise a
 * KeyError whose message is the model name, kept as a fallback.
 */
export function isModuleNotInstalled(err: unknown, model?: string): boolean {
  if (!err || typeof err !== "object") return false;
  const { kind, message } = err as { kind?: unknown; message?: unknown };
  if (kind === "module_not_installed") return true;
  return !!model && kind === "request_failed" && typeof message === "string" && message.includes(model);
}

/** The model each optional part of the app depends on. */
export const FEATURE_MODELS = {
  work: "security.work.task",
  training: "security.training.assignment",
  adoption: "security.adoption.snapshot",
  inbox: "security.exception.instance",
  owner: "security.owner.digest",
  help: "security.help.article",
  support: "security.support.request",
} as const;

export type Feature = keyof typeof FEATURE_MODELS;
/** `false` only when the server has positively said the module is missing. */
export type Capabilities = Partial<Record<Feature, boolean>>;

/**
 * Asks the server which optional modules it has. A failure for any other
 * reason (offline, a permissions quirk) counts as "available": hiding a
 * screen someone needs because of a network blip is worse than showing one
 * that then explains its own error.
 */
export async function probeCapabilities(): Promise<Capabilities> {
  const entries = await Promise.all(
    (Object.keys(FEATURE_MODELS) as Feature[]).map(async (feature) => {
      const model = FEATURE_MODELS[feature];
      try {
        await callKw(model, "fields_get", [], { attributes: ["type"] });
        return [feature, true] as const;
      } catch (err) {
        return [feature, !isModuleNotInstalled(err, model)] as const;
      }
    }),
  );
  return Object.fromEntries(entries);
}

export function isAvailable(caps: Capabilities, feature: Feature): boolean {
  return caps[feature] !== false;
}
