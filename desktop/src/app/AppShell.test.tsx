// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { backend } from "../test/fakeTauri";
import { AppShell } from "./AppShell";
import { ViewModeProvider } from "./viewMode";
import { SessionProviderRoot } from "../session/SessionContext";
import { ConnectivityProvider } from "../lib/connectivity";
import { clearEmployeeIdCache } from "../api/work";

const employee = { uid: 7, login: "ops@dogforce.example", name: "Grace Mwale", db: "dogforce_prod" };
const acknowledgedNotice = { version: "v1", title: "Notice", body: ["n"], acknowledged: true, acknowledged_at: "2026-09-01 08:00:00" };

interface ServerOptions {
  missing?: string[];
  viewer?: { is_supervisor: boolean; is_manager: boolean; is_owner: boolean } | "no_endpoint";
  notice?: typeof acknowledgedNotice | "missing";
}

/** Configures the fake Odoo: which modules exist, who the viewer is, notice state. */
function server({ missing = [], viewer = { is_supervisor: false, is_manager: false, is_owner: false }, notice = acknowledgedNotice }: ServerOptions) {
  backend.callKw = async (model, method) => {
    if (missing.includes(model)) throw { kind: "module_not_installed", message: "This feature isn't installed" };
    if (method === "fields_get") return {};
    if (method === "get_viewer_context") {
      if (viewer === "no_endpoint") throw { kind: "request_failed", message: "no such method" };
      return viewer;
    }
    if (model === "security.deployguard.policy.acknowledgement") {
      if (notice === "missing") throw { kind: "module_not_installed", message: "x" };
      return method === "acknowledge" ? { ...notice, acknowledged: true } : notice;
    }
    if (method === "search_read" || method === "get_my_today") return [];
    return null;
  };
}

function renderApp() {
  return render(
    <SessionProviderRoot>
      <ConnectivityProvider>
        <ViewModeProvider>
          <AppShell />
        </ViewModeProvider>
      </ConnectivityProvider>
    </SessionProviderRoot>,
  );
}

async function openApp() {
  fireEvent.click(await screen.findByRole("button", { name: "Open DeployGuard" }));
  return screen.findByRole("navigation", { name: "DeployGuard sections" });
}

beforeEach(() => {
  backend.reset();
  backend.session = employee;
  clearEmployeeIdCache();
  window.localStorage.clear();
  window.localStorage.setItem(`dg.welcome.seen.${employee.db}.${employee.uid}`, "1");
});
afterEach(cleanup);

describe("AppShell: pages follow what the server supports", () => {
  it("hides a screen whose Odoo module isn't installed", async () => {
    server({ missing: ["security.exception.instance"] });
    renderApp();
    const nav = await openApp();
    await waitFor(() => expect(within(nav).queryByText("Exceptions")).toBeNull());
    expect(within(nav).getByText("My Work")).toBeTruthy();
  });

  it("hides manager and owner pages from an employee, as decided by the server", async () => {
    server({ viewer: { is_supervisor: false, is_manager: false, is_owner: false } });
    renderApp();
    const nav = await openApp();
    await waitFor(() => expect(within(nav).queryByText("Owner Overview")).toBeNull());
    expect(within(nav).queryByText("Team Today")).toBeNull();
  });

  it("shows the owner the Owner Overview", async () => {
    server({ viewer: { is_supervisor: false, is_manager: false, is_owner: true } });
    renderApp();
    const nav = await openApp();
    expect(await within(nav).findByText("Owner Overview")).toBeTruthy();
  });

  it("keeps working against an older server without the viewer endpoint", async () => {
    server({ viewer: "no_endpoint" });
    renderApp();
    const nav = await openApp();
    expect(await within(nav).findByText("My Work")).toBeTruthy();
  });
});

describe("AppShell: first run", () => {
  it("opens onboarding with the monitoring notice until it is acknowledged", async () => {
    window.localStorage.clear();
    server({ notice: { ...acknowledgedNotice, acknowledged: false } });
    renderApp();
    expect(await screen.findByRole("region", { name: "Getting started" })).toBeTruthy();
    expect(backend.viewMode).toBe("app");
  });

  it("does not show onboarding again on a repeat launch", async () => {
    server({});
    renderApp();
    await openApp();
    expect(screen.queryByRole("region", { name: "Getting started" })).toBeNull();
  });

  it("does not re-open onboarding when Rust re-announces the same sign-in after an Odoo page load", async () => {
    server({});
    renderApp();
    await openApp();
    act(() => backend.emit("deployguard://session-changed", { status: "signed_in", session: { ...employee }, auto_reveal: false }));
    expect(screen.queryByRole("region", { name: "Getting started" })).toBeNull();
  });
});

describe("AppShell: session expiry", () => {
  it("tells the employee their session expired instead of silently signing them out", async () => {
    server({});
    renderApp();
    await openApp();
    act(() => backend.emit("deployguard://session-changed", { status: "expired" }));
    act(() => backend.emit("deployguard://view-mode", "app"));
    expect(await screen.findByText("Your session expired")).toBeTruthy();
  });
});
