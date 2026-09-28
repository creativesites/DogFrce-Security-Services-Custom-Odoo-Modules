import type { ReactNode } from "react";
import { extractErrorMessage } from "../lib/extractErrorMessage";

/** Screen-level empty state: says plainly that there is nothing, and what to do. */
export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="dg-empty" role="status">
      <h3 className="dg-empty__title">{title}</h3>
      {children && <div className="dg-empty__body">{children}</div>}
      {action && <div className="dg-empty__action">{action}</div>}
    </div>
  );
}

/**
 * Screen-level error. Always a human sentence (via extractErrorMessage), never
 * "[object Object]", and always with a way forward.
 */
export function ErrorState({ error, fallback, onRetry }: { error: unknown; fallback?: string; onRetry?: () => void }) {
  return (
    <div className="dg-alert dg-alert--danger" role="alert">
      <span>{extractErrorMessage(error, fallback)}</span>
      {onRetry && (
        <button type="button" className="dg-btn dg-btn--secondary dg-btn--sm" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <span className="dg-spinner" role="status">
      <span className="dg-sr-only">{label}</span>
    </span>
  );
}

export type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger";

export function Badge({ tone = "neutral", children }: { tone?: BadgeTone; children: ReactNode }) {
  return <span className={`dg-badge dg-badge--${tone}`}>{children}</span>;
}
