import type { ReactNode } from "react";
import { SparklesIcon, CheckCircleIcon } from "../shell/icons";

export interface AttentionItem {
  id: string;
  tone: "danger" | "warning" | "info" | "success";
  title: string;
  detail: string;
  actionLabel?: string;
  onAction?: () => void;
}

export interface AttentionCardProps {
  title: string;
  subtitle?: string;
  badge?: string;
  items: AttentionItem[];
  emptyMessage?: string;
  footer?: ReactNode;
}

export function AttentionCard({
  title,
  subtitle,
  badge = "AI Insight",
  items,
  emptyMessage = "All operations are currently running on track with no urgent issues.",
  footer,
}: AttentionCardProps) {
  const hasItems = items.length > 0;

  return (
    <section className="dg-attention-card dg-panel" aria-labelledby="dg-attention-title">
      <div className="dg-attention-head">
        <div className="dg-attention-title-wrap">
          <span className="dg-attention-spark" aria-hidden="true">
            <SparklesIcon size={18} />
          </span>
          <div>
            <h2 id="dg-attention-title" className="dg-attention-title">{title}</h2>
            {subtitle && <p className="dg-attention-subtitle">{subtitle}</p>}
          </div>
        </div>
        {badge && <span className="dg-attention-badge">{badge}</span>}
      </div>

      {!hasItems ? (
        <div className="dg-attention-clean">
          <CheckCircleIcon size={20} />
          <span>{emptyMessage}</span>
        </div>
      ) : (
        <ul className="dg-attention-list">
          {items.map((item) => (
            <li key={item.id} className={`dg-attention-item dg-attention-item--${item.tone}`}>
              <span className={`dg-attention-dot dg-attention-dot--${item.tone}`} aria-hidden="true" />
              <div className="dg-attention-content">
                <span className="dg-attention-item-title">{item.title}</span>
                <span className="dg-attention-item-detail">{item.detail}</span>
              </div>
              {item.actionLabel && item.onAction && (
                <button
                  type="button"
                  className="dg-btn dg-btn--sm dg-attention-action"
                  onClick={item.onAction}
                >
                  {item.actionLabel}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {footer && <div className="dg-attention-footer">{footer}</div>}
    </section>
  );
}
