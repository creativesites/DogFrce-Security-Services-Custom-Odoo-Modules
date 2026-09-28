import { emit } from "./bus";
import { fakeOdoo } from "./fakeOdoo";

/**
 * Fake native side. URL parameters pick the scenario:
 *   ?as=ops|admin|hr|gm|owner   who is signed in (default ops)
 *   &state=signed_out|expired   session state
 *   &mode=app|odoo|guide_dock   initial window layout (default app)
 *   &guide=off_track|done       guide dock variant
 *   &first=1                    first run (monitoring notice not acknowledged)
 */
const params = new URLSearchParams(window.location.search);
let viewMode = params.get("mode") || "app";

export const PEOPLE = {
  ops: { uid: 7, login: "grace@dogforce.example", name: "Grace Mwale", db: "dogforce_prod" },
  admin: { uid: 8, login: "joseph@dogforce.example", name: "Joseph Phiri", db: "dogforce_prod" },
  hr: { uid: 9, login: "ruth@dogforce.example", name: "Ruth Banda", db: "dogforce_prod" },
  gm: { uid: 4, login: "wilbert@dogforce.example", name: "Wilbert Chanda", db: "dogforce_prod" },
  owner: { uid: 2, login: "kuume@dogforce.example", name: "Kuume Mulenga", db: "dogforce_prod" },
} as const;

export const who = (params.get("as") || "ops") as keyof typeof PEOPLE;
const state = params.get("state");

export async function invoke(cmd: string, args: Record<string, unknown> = {}): Promise<unknown> {
  await new Promise((r) => setTimeout(r, 60));
  switch (cmd) {
    case "get_current_session":
      return state ? null : PEOPLE[who];
    case "get_view_mode":
      return viewMode;
    case "set_view_mode":
      viewMode = args.mode as string;
      emit("deployguard://view-mode", viewMode);
      return null;
    case "connectivity_check":
      return params.get("net") === "offline"
        ? { state: "offline", message: "This computer isn't connected to a network." }
        : { state: "online", message: "" };
    case "odoo_fetch_avatar":
      return null;
    case "diagnostics_get":
      return { app_version: "0.3.0", os: "Windows 11", odoo_base_url: "https://dogforcesecurityservices.com",
        odoo_reachable: true, signed_in: false, last_sync_note: "signed out", log_dir: "C:\\Users\\…\\logs" };
    case "odoo_call_kw":
      return fakeOdoo(args.model as string, args.method as string, (args.args as unknown[]) ?? [], (args.kwargs as Record<string, unknown>) ?? {});
    default:
      return null;
  }
}

if (state === "expired") setTimeout(() => emit("deployguard://session-changed", { status: "expired" }), 300);
