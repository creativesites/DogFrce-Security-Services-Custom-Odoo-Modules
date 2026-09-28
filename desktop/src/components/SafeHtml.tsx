import DOMPurify from "dompurify";
import { useMemo } from "react";

/**
 * Renders server-authored HTML (help articles, lesson bodies, guidance help)
 * after sanitising it. The CSP already refuses inline script, but the shell
 * webview holds IPC access, so it doesn't rely on a single barrier: scripts,
 * event handlers, forms, iframes and `javascript:` URLs are all stripped here.
 */
export function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["style", "form", "input", "button", "iframe", "object", "embed", "script"],
    FORBID_ATTR: ["style"],
  });
}

export function SafeHtml({ html, className }: { html: string | null | undefined; className?: string }) {
  const clean = useMemo(() => sanitizeHtml(html ?? ""), [html]);
  return <div className={className} dangerouslySetInnerHTML={{ __html: clean }} />;
}
