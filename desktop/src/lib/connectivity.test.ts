import { describe, expect, it } from "vitest";
import { effectiveConnectivity } from "./connectivity";

describe("effectiveConnectivity", () => {
  it("reports an expired session while the network is fine", () => {
    expect(effectiveConnectivity({ state: "online", message: "" }, true).state).toBe("auth_expired");
  });

  it("reports the network problem first when there is one", () => {
    expect(effectiveConnectivity({ state: "offline", message: "x" }, true).state).toBe("offline");
    expect(effectiveConnectivity({ state: "odoo_unreachable", message: "x" }, true).state).toBe("odoo_unreachable");
  });

  it("passes the network state through otherwise", () => {
    expect(effectiveConnectivity({ state: "online", message: "" }, false).state).toBe("online");
  });
});
