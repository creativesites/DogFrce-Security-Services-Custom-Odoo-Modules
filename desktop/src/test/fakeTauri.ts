import { vi } from "vitest";

/**
 * A fake of the native side for component tests: the Tauri commands the shell
 * calls, and the events Rust emits. Each test configures `backend.callKw` to
 * answer Odoo calls the way a particular server would.
 */
type Listener = (event: { payload: unknown }) => void;

export const backend = {
  session: null as null | { uid: number; login: string; name: string; db: string },
  viewMode: "odoo" as "odoo" | "app" | "guide_dock",
  callKw: (async () => { throw { kind: "module_not_installed", message: "x" }; }) as (
    model: string, method: string, args: unknown[], kwargs: Record<string, unknown>,
  ) => Promise<unknown>,
  listeners: new Map<string, Set<Listener>>(),
  invoked: [] as Array<{ cmd: string; args?: Record<string, unknown> }>,
  emit(name: string, payload: unknown) {
    for (const l of this.listeners.get(name) ?? []) l({ payload });
  },
  reset() {
    this.session = null;
    this.viewMode = "odoo";
    this.listeners.clear();
    this.invoked = [];
  },
};

async function invoke(cmd: string, args?: Record<string, unknown>): Promise<unknown> {
  backend.invoked.push({ cmd, args });
  switch (cmd) {
    case "get_current_session":
      return backend.session;
    case "get_view_mode":
      return backend.viewMode;
    case "set_view_mode":
      backend.viewMode = args?.mode as typeof backend.viewMode;
      backend.emit("deployguard://view-mode", backend.viewMode);
      return null;
    case "connectivity_check":
      return { state: "online", message: "" };
    case "odoo_fetch_avatar":
      return null;
    case "odoo_call_kw":
      return backend.callKw(
        args?.model as string, args?.method as string, (args?.args as unknown[]) ?? [],
        (args?.kwargs as Record<string, unknown>) ?? {},
      );
    default:
      return null;
  }
}

vi.mock("@tauri-apps/api/core", () => ({ invoke }));
vi.mock("@tauri-apps/api/event", () => ({
  listen: async (name: string, cb: Listener) => {
    if (!backend.listeners.has(name)) backend.listeners.set(name, new Set());
    backend.listeners.get(name)!.add(cb);
    return () => backend.listeners.get(name)?.delete(cb);
  },
}));
vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: () => ({ isMaximized: async () => false, onResized: async () => () => {} }),
}));
vi.mock("@tauri-apps/api/app", () => ({ getVersion: async () => "0.3.0" }));
vi.mock("@tauri-apps/plugin-updater", () => ({ check: async () => null }));
vi.mock("@tauri-apps/plugin-process", () => ({ relaunch: async () => {} }));
vi.mock("@tauri-apps/plugin-notification", () => ({
  isPermissionGranted: async () => false, requestPermission: async () => "denied", sendNotification: () => {},
}));
