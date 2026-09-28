// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { sanitizeHtml } from "./SafeHtml";

describe("sanitizeHtml", () => {
  it("keeps ordinary lesson formatting", () => {
    expect(sanitizeHtml("<h2>Step 1</h2><p>Open <strong>Attendance</strong></p>")).toBe(
      "<h2>Step 1</h2><p>Open <strong>Attendance</strong></p>",
    );
  });

  it("strips scripts, inline handlers and javascript: links", () => {
    const out = sanitizeHtml(
      '<p onclick="steal()">x</p><script>alert(1)</script><img src=x onerror="alert(1)"><a href="javascript:alert(1)">y</a>',
    );
    expect(out).not.toMatch(/script|onclick|onerror|javascript:/i);
  });

  it("strips embedded frames and forms", () => {
    expect(sanitizeHtml('<iframe src="https://evil"></iframe><form action="/x"><input></form>')).toBe("");
  });
});
