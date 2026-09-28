import { useEffect, useId, useRef, type ReactNode } from "react";

interface ModalProps {
  title: ReactNode;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  /** "dialog" is centred; "drawer" slides in from the right edge. */
  variant?: "dialog" | "drawer";
  size?: "sm" | "md" | "lg";
  subtitle?: ReactNode;
  /** Disable closing (Escape, backdrop, ✕) while something is in flight. */
  busy?: boolean;
}

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * The one modal primitive. Replaces five hand-rolled variants that each
 * handled (or didn't handle) Escape, focus and the backdrop differently.
 * Focus moves into the dialog on open, is trapped while open, and returns to
 * whatever had it before when closed (AGENT-FINDINGS: "Escape not returning
 * focus").
 */
export function Modal({ title, subtitle, onClose, children, footer, variant = "dialog", size = "md", busy = false }: ModalProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const busyRef = useRef(busy);
  busyRef.current = busy;

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    const first = panel?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? panel)?.focus();

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.stopPropagation();
        if (!busyRef.current) onCloseRef.current();
        return;
      }
      if (e.key !== "Tab" || !panel) return;
      const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (items.length === 0) return;
      const firstEl = items[0];
      const lastEl = items[items.length - 1];
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    }
    document.addEventListener("keydown", onKeyDown, true);
    return () => {
      document.removeEventListener("keydown", onKeyDown, true);
      previouslyFocused?.focus?.();
    };
  }, []);

  return (
    <div className={`dg-modal-backdrop dg-modal-backdrop--${variant}`} onMouseDown={(e) => { if (e.target === e.currentTarget && !busy) onClose(); }}>
      <div
        ref={panelRef}
        className={`dg-modal dg-modal--${variant} dg-modal--${size}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
      >
        <header className="dg-modal__head">
          <div>
            <h2 id={titleId} className="dg-modal__title">{title}</h2>
            {subtitle && <div className="dg-modal__subtitle">{subtitle}</div>}
          </div>
          <button type="button" className="dg-iconbtn" aria-label="Close" onClick={onClose} disabled={busy}>✕</button>
        </header>
        <div className="dg-modal__body">{children}</div>
        {footer && <footer className="dg-modal__foot">{footer}</footer>}
      </div>
    </div>
  );
}
