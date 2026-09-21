import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchExceptions,
  getExceptionCounts,
  acknowledgeException,
  resolveException,
  dismissException,
  syncExceptions,
  type ExceptionInstance,
  type ExceptionCounts,
  type ResolutionCode,
  RESOLUTION_CODE_LABELS,
} from "../../api/exceptions";
import { notifyDesktop } from "../../lib/notifications";
import { invoke } from "../../lib/tauri";
import {
  AlertTriangleIcon,
  AlertOctagonIcon,
  CheckCircleIcon,
  CheckCheckIcon,
  ClockIcon,
  ExternalLinkIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from "../icons";

type InboxTab = "critical" | "attention" | "watch" | "all_open" | "history";

const RESOLUTION_OPTIONS: { code: ResolutionCode; label: string; desc: string }[] = [
  { code: "fixed", label: "Fixed", desc: "Action taken, deficiency directly corrected" },
  { code: "covered", label: "Covered", desc: "Shift gap or absence filled by reserve guard" },
  { code: "explained", label: "Explained", desc: "Valid operational justification documented" },
  { code: "not_an_issue", label: "Not an Issue", desc: "False positive, simulation, or non-actionable" },
  { code: "duplicate", label: "Duplicate", desc: "Addressed in another incident or ticket" },
  { code: "deferred", label: "Deferred", desc: "Scheduled for maintenance / authorized delay" },
];

export function ExceptionsInbox() {
  const [items, setItems] = useState<ExceptionInstance[]>([]);
  const [counts, setCounts] = useState<ExceptionCounts>({
    critical: 0,
    attention: 0,
    watch: 0,
    totalOpen: 0,
  });
  const [tab, setTab] = useState<InboxTab>("critical");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Resolution modal state
  const [resolvingItem, setResolvingItem] = useState<ExceptionInstance | null>(null);
  const [resolutionCode, setResolutionCode] = useState<ResolutionCode>("fixed");
  const [resolutionNote, setResolutionNote] = useState("");

  // Track known IDs to send desktop notification on new arrivals
  const knownCriticalIds = useRef<Set<number>>(new Set());
  const initialLoadDone = useRef(false);

  const loadData = useCallback(async (isBackground = false) => {
    if (!isBackground) setLoading(true);
    setError(null);

    try {
      const newCounts = await getExceptionCounts();
      setCounts(newCounts);

      let filters = {};
      if (tab === "critical") {
        filters = { tier: "critical", state: ["open", "stale_paused", "acknowledged"] };
      } else if (tab === "attention") {
        filters = { tier: "attention", state: ["open", "stale_paused", "acknowledged"] };
      } else if (tab === "watch") {
        filters = { tier: "watch", state: ["open", "stale_paused", "acknowledged"] };
      } else if (tab === "all_open") {
        filters = { state: ["open", "stale_paused", "acknowledged"] };
      } else if (tab === "history") {
        filters = { state: ["resolved", "auto_resolved"] };
      }

      const list = await fetchExceptions(filters);
      setItems(list);
      setSelectedIndex((prev) => (list.length === 0 ? 0 : Math.min(prev, list.length - 1)));

      // Check for newly arrived critical items
      const criticals = list.filter((it) => it.tier === "critical" && it.state === "open");
      if (initialLoadDone.current) {
        for (const crit of criticals) {
          if (!knownCriticalIds.current.has(crit.id)) {
            void notifyDesktop({
              title: `🚨 Critical Exception: ${crit.title}`,
              body: crit.body ? String(crit.body) : "Immediate operational triage required.",
            });
          }
        }
      }
      for (const crit of criticals) {
        knownCriticalIds.current.add(crit.id);
      }
      initialLoadDone.current = true;
    } catch (err) {
      console.error("Failed to load exceptions:", err);
      setError(err instanceof Error ? err.message : "Failed to load exceptions");
    } finally {
      if (!isBackground) setLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  // Periodic background refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      void loadData(true);
    }, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  // Handle manual sync from source notifications
  const handleSync = useCallback(async () => {
    setSyncing(true);
    try {
      await syncExceptions();
      await loadData(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }, [loadData]);

  // Triage: Acknowledge
  const handleAcknowledge = useCallback(async (item: ExceptionInstance) => {
    setActionLoading(true);
    try {
      await acknowledgeException(item.id);
      await loadData(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Acknowledge failed");
    } finally {
      setActionLoading(false);
    }
  }, [loadData]);

  // Triage: Dismiss as non-issue
  const handleDismiss = async (item: ExceptionInstance) => {
    setActionLoading(true);
    try {
      await dismissException(item.id, "Dismissed via Manager Inbox");
      await loadData(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dismissal failed");
    } finally {
      setActionLoading(false);
    }
  };

  // Triage: Open Resolution Dialog
  const openResolveModal = useCallback((item: ExceptionInstance) => {
    setResolvingItem(item);
    setResolutionCode("fixed");
    setResolutionNote("");
  }, []);

  // Triage: Submit Resolution
  const handleResolveSubmit = async () => {
    if (!resolvingItem) return;
    setActionLoading(true);
    try {
      await resolveException(resolvingItem.id, resolutionCode, resolutionNote);
      setResolvingItem(null);
      await loadData(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resolution failed");
    } finally {
      setActionLoading(false);
    }
  };

  // Deep link into Odoo record
  const handleOpenRecord = useCallback(async (item: ExceptionInstance) => {
    let path = "/odoo/action-security_exceptions.action_exception_instance";
    if (item.related_model && item.related_id) {
      path = `/web#model=${item.related_model}&id=${item.related_id}`;
    }
    try {
      await invoke("navigate_odoo", { path });
    } catch (err) {
      console.warn("Could not navigate in desktop webview:", err);
    }
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // If modal is open, handle Escape
      if (resolvingItem) {
        if (e.key === "Escape") {
          e.preventDefault();
          setResolvingItem(null);
        }
        return;
      }

      // Ignore keyboard shortcuts if focus is inside an input/textarea
      const activeTag = document.activeElement?.tagName?.toLowerCase();
      if (activeTag === "input" || activeTag === "textarea") return;

      if (e.key === "ArrowDown" || e.key === "j") {
        e.preventDefault();
        setSelectedIndex((idx) => Math.min(idx + 1, Math.max(items.length - 1, 0)));
      } else if (e.key === "ArrowUp" || e.key === "k") {
        e.preventDefault();
        setSelectedIndex((idx) => Math.max(idx - 1, 0));
      } else if (e.key === "a") {
        e.preventDefault();
        const activeItem = items[selectedIndex];
        if (activeItem && activeItem.state !== "acknowledged" && activeItem.state !== "resolved") {
          void handleAcknowledge(activeItem);
        }
      } else if (e.key === "e") {
        e.preventDefault();
        const activeItem = items[selectedIndex];
        if (activeItem && activeItem.state !== "resolved" && activeItem.state !== "auto_resolved") {
          openResolveModal(activeItem);
        }
      } else if (e.key === "Enter") {
        e.preventDefault();
        const activeItem = items[selectedIndex];
        if (activeItem) {
          void handleOpenRecord(activeItem);
        }
      } else if (e.key === "s") {
        e.preventDefault();
        void handleSync();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [resolvingItem, items, selectedIndex, handleAcknowledge, handleSync, handleOpenRecord, openResolveModal]);

  const activeItem = items[selectedIndex] || null;

  return (
    <div className="dg-inbox-page">
      {/* Header */}
      <header className="dg-inbox-header">
        <div className="dg-inbox-header__titles">
          <div className="dg-inbox-header__eyebrow">
            <ShieldCheckIcon size={16} />
            <span>Operational Reliability Engine</span>
          </div>
          <h1 className="dg-inbox-header__title">Exceptions & Triage Inbox</h1>
          <p className="dg-inbox-header__subline">
            Rule-driven ingest from alerts · Escalation working hours · Two-interaction resolution
          </p>
        </div>

        <div className="dg-inbox-header__actions">
          <button
            type="button"
            className="dg-btn dg-btn--secondary"
            onClick={() => void handleSync()}
            disabled={syncing}
            title="Ingest open notifications and refresh escalation clock (Press 's')"
          >
            <ClockIcon size={15} />
            {syncing ? "Syncing..." : "Sync Alerts"}
          </button>
          <button
            type="button"
            className="dg-btn dg-btn--secondary"
            onClick={() => void invoke("navigate_odoo", { path: "/odoo/action-security_exceptions.action_exception_instance" })}
            title="Open native Odoo backend exceptions table"
          >
            <ExternalLinkIcon size={15} />
            Odoo Table
          </button>
        </div>
      </header>

      {/* Tier Tabs */}
      <nav className="dg-inbox-tabs" aria-label="Exception Tiers">
        <button
          type="button"
          className={`dg-inbox-tab dg-inbox-tab--critical ${tab === "critical" ? "is-active" : ""}`}
          onClick={() => setTab("critical")}
        >
          <AlertOctagonIcon size={16} />
          <span>Critical · Act Now</span>
          {counts.critical > 0 && (
            <span className="dg-inbox-tab__badge dg-inbox-tab__badge--critical">
              {counts.critical}
            </span>
          )}
        </button>

        <button
          type="button"
          className={`dg-inbox-tab dg-inbox-tab--attention ${tab === "attention" ? "is-active" : ""}`}
          onClick={() => setTab("attention")}
        >
          <AlertTriangleIcon size={16} />
          <span>Attention · Today</span>
          {counts.attention > 0 && (
            <span className="dg-inbox-tab__badge dg-inbox-tab__badge--attention">
              {counts.attention}
            </span>
          )}
        </button>

        <button
          type="button"
          className={`dg-inbox-tab dg-inbox-tab--watch ${tab === "watch" ? "is-active" : ""}`}
          onClick={() => setTab("watch")}
        >
          <ClockIcon size={16} />
          <span>Watch · This Week</span>
          {counts.watch > 0 && (
            <span className="dg-inbox-tab__badge dg-inbox-tab__badge--watch">
              {counts.watch}
            </span>
          )}
        </button>

        <button
          type="button"
          className={`dg-inbox-tab ${tab === "all_open" ? "is-active" : ""}`}
          onClick={() => setTab("all_open")}
        >
          <span>All Open</span>
          <span className="dg-inbox-tab__badge">{counts.totalOpen}</span>
        </button>

        <button
          type="button"
          className={`dg-inbox-tab ${tab === "history" ? "is-active" : ""}`}
          onClick={() => setTab("history")}
        >
          <CheckCheckIcon size={16} />
          <span>Resolved History</span>
        </button>
      </nav>

      {/* Keyboard Shortcuts Hint Bar */}
      <div className="dg-inbox-hotkeys">
        <span className="dg-inbox-hotkeys__hint">
          <kbd>j</kbd>/<kbd>k</kbd> Navigate
        </span>
        <span className="dg-inbox-hotkeys__hint">
          <kbd>a</kbd> Acknowledge
        </span>
        <span className="dg-inbox-hotkeys__hint">
          <kbd>e</kbd> Resolve
        </span>
        <span className="dg-inbox-hotkeys__hint">
          <kbd>↵</kbd> Open ERP Record
        </span>
        <span className="dg-inbox-hotkeys__hint">
          <kbd>s</kbd> Sync
        </span>
      </div>

      {error && (
        <div className="dg-inbox-error">
          <AlertTriangleIcon size={16} />
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)} className="dg-inbox-error__dismiss">
            ×
          </button>
        </div>
      )}

      {/* Main Content Area: Split View (List + Inspector) */}
      <div className="dg-inbox-layout">
        {/* Left Column: Exception Cards */}
        <section className="dg-inbox-list" aria-label="Exceptions List">
          {loading ? (
            <div className="dg-inbox-loading">
              <div className="dg-spinner" />
              <span>Loading operational exceptions...</span>
            </div>
          ) : items.length === 0 ? (
            <div className="dg-inbox-empty">
              <div className="dg-inbox-empty__icon">
                <CheckCircleIcon size={38} />
              </div>
              <h3 className="dg-inbox-empty__title">
                {tab === "critical"
                  ? "Zero Critical Exceptions"
                  : tab === "attention"
                  ? "Attention Tier is Clear"
                  : tab === "watch"
                  ? "Watch Tier is Clear"
                  : tab === "history"
                  ? "No Resolved Records Yet"
                  : "Inbox Zero — Ops Running Cleanly"}
              </h3>
              <p className="dg-inbox-empty__subline">
                {tab === "critical"
                  ? "All guard posts, AWOL alerts, and critical SLAs are covered."
                  : "No pending triage items in this view."}
              </p>
            </div>
          ) : (
            <div className="dg-inbox-cards" role="listbox">
              {items.map((item, index) => {
                const isSelected = index === selectedIndex;
                const isAck = item.state === "acknowledged";
                const isPaused = item.state === "stale_paused";
                const isResolved = item.state === "resolved" || item.state === "auto_resolved";

                return (
                  <article
                    key={item.id}
                    role="option"
                    aria-selected={isSelected}
                    className={`dg-inbox-card dg-inbox-card--${item.tier}${
                      isSelected ? " is-selected" : ""
                    }${isAck ? " is-acknowledged" : ""}${isResolved ? " is-resolved" : ""}`}
                    onClick={() => setSelectedIndex(index)}
                  >
                    <div className="dg-inbox-card__header">
                      <span className={`dg-tier-tag dg-tier-tag--${item.tier}`}>
                        {item.tier.toUpperCase()}
                      </span>
                      {item.escalation_level > 0 && (
                        <span className="dg-escalation-tag">
                          L{item.escalation_level} Escalated
                        </span>
                      )}
                      {isPaused && (
                        <span className="dg-paused-tag" title="Escalation paused on stale data">
                          Data Paused
                        </span>
                      )}
                      <span className="dg-inbox-card__time">
                        {new Date(item.first_seen_at.replace(" ", "T") + "Z").toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>

                    <h4 className="dg-inbox-card__title">{item.title}</h4>
                    {item.body && <p className="dg-inbox-card__snippet">{item.body}</p>}

                    <div className="dg-inbox-card__footer">
                      <span className="dg-inbox-card__site">
                        {Array.isArray(item.site_id) ? item.site_id[1] : "All Sites / System"}
                      </span>
                      <span className="dg-inbox-card__state-pill">
                        {item.state === "auto_resolved"
                          ? "Auto-resolved"
                          : item.state === "stale_paused"
                          ? "Paused"
                          : item.state}
                      </span>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        {/* Right Column: Selected Item Detail & Triage Console */}
        <aside className="dg-inbox-detail" aria-label="Exception Details">
          {activeItem ? (
            <div className="dg-inbox-detail__panel">
              <div className="dg-inbox-detail__top">
                <div className="dg-inbox-detail__meta-tags">
                  <span className={`dg-tier-tag dg-tier-tag--${activeItem.tier}`}>
                    Tier: {activeItem.tier.toUpperCase()}
                  </span>
                  <span className="dg-status-tag">Status: {activeItem.state}</span>
                  {activeItem.escalation_level > 0 && (
                    <span className="dg-escalation-tag">
                      Escalation Level {activeItem.escalation_level}
                    </span>
                  )}
                </div>

                <h2 className="dg-inbox-detail__title">{activeItem.title}</h2>
                <div className="dg-inbox-detail__site-banner">
                  <strong>Site:</strong>{" "}
                  {Array.isArray(activeItem.site_id) ? activeItem.site_id[1] : "Central / All Sites"}
                </div>
              </div>

              {activeItem.body && (
                <div className="dg-inbox-detail__body-box">
                  <div className="dg-inbox-detail__body-label">Details / Condition:</div>
                  <div className="dg-inbox-detail__body-text">{activeItem.body}</div>
                </div>
              )}

              {/* Triage & Escalation Info */}
              <div className="dg-inbox-detail__audit">
                <div className="dg-inbox-detail__audit-row">
                  <span className="dg-audit-label">First Seen:</span>
                  <span className="dg-audit-val">{activeItem.first_seen_at}</span>
                </div>
                <div className="dg-inbox-detail__audit-row">
                  <span className="dg-audit-label">Last Confirmed:</span>
                  <span className="dg-audit-val">{activeItem.last_confirmed_at}</span>
                </div>
                {activeItem.acknowledged_at && (
                  <div className="dg-inbox-detail__audit-row">
                    <span className="dg-audit-label">Acknowledged:</span>
                    <span className="dg-audit-val">
                      {activeItem.acknowledged_at}{" "}
                      {Array.isArray(activeItem.acknowledged_by_id)
                        ? `by ${activeItem.acknowledged_by_id[1]}`
                        : ""}
                    </span>
                  </div>
                )}
                {activeItem.resolution_code && (
                  <div className="dg-inbox-detail__audit-row dg-inbox-detail__audit-row--highlight">
                    <span className="dg-audit-label">Resolution:</span>
                    <span className="dg-audit-val">
                      <strong>{RESOLUTION_CODE_LABELS[activeItem.resolution_code]}</strong>
                      {activeItem.resolution_note ? ` — ${activeItem.resolution_note}` : ""}
                    </span>
                  </div>
                )}
              </div>

              {/* Action Toolbar (Two-Interaction Rule) */}
              <div className="dg-inbox-detail__actions">
                {activeItem.state !== "acknowledged" &&
                  activeItem.state !== "resolved" &&
                  activeItem.state !== "auto_resolved" && (
                    <button
                      type="button"
                      className="dg-btn dg-btn--secondary"
                      onClick={() => void handleAcknowledge(activeItem)}
                      disabled={actionLoading}
                      title="Acknowledge exception to halt further escalation (Press 'a')"
                    >
                      <CheckCircleIcon size={16} />
                      Acknowledge
                    </button>
                  )}

                {activeItem.state !== "resolved" && activeItem.state !== "auto_resolved" && (
                  <>
                    <button
                      type="button"
                      className="dg-btn dg-btn--primary"
                      onClick={() => openResolveModal(activeItem)}
                      disabled={actionLoading}
                      title="Select resolution code and close this exception (Press 'e')"
                    >
                      <CheckCheckIcon size={16} />
                      Resolve...
                    </button>
                    <button
                      type="button"
                      className="dg-btn dg-btn--secondary"
                      onClick={() => void handleDismiss(activeItem)}
                      disabled={actionLoading}
                      title="Dismiss as non-issue / false alarm"
                    >
                      Dismiss
                    </button>
                  </>
                )}

                {activeItem.related_model && activeItem.related_id && (
                  <button
                    type="button"
                    className="dg-btn dg-btn--ghost"
                    onClick={() => void handleOpenRecord(activeItem)}
                    title={`Open source record in ERP (${activeItem.related_model} #${activeItem.related_id}) (Press Enter)`}
                  >
                    <ExternalLinkIcon size={16} />
                    Open Record
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="dg-inbox-detail__empty">
              <SparklesIcon size={32} />
              <p>Select an exception to review details and take rapid triage action.</p>
            </div>
          )}
        </aside>
      </div>

      {/* Resolution Modal */}
      {resolvingItem && (
        <div className="dg-modal-backdrop" onClick={() => setResolvingItem(null)}>
          <div
            className="dg-modal dg-resolution-modal"
            role="dialog"
            aria-labelledby="dg-res-title"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="dg-modal__header">
              <h3 id="dg-res-title" className="dg-modal__title">
                Resolve Exception
              </h3>
              <button
                type="button"
                className="dg-modal__close"
                onClick={() => setResolvingItem(null)}
                aria-label="Close"
              >
                ×
              </button>
            </header>

            <div className="dg-modal__body">
              <p className="dg-modal__subtext">
                Target: <strong>{resolvingItem.title}</strong>
              </p>

              <div className="dg-resolution-options">
                <label className="dg-resolution-label">Resolution Code:</label>
                <div className="dg-resolution-grid">
                  {RESOLUTION_OPTIONS.map((opt) => (
                    <label
                      key={opt.code}
                      className={`dg-resolution-choice ${
                        resolutionCode === opt.code ? "is-selected" : ""
                      }`}
                    >
                      <input
                        type="radio"
                        name="resolutionCode"
                        value={opt.code}
                        checked={resolutionCode === opt.code}
                        onChange={() => setResolutionCode(opt.code)}
                      />
                      <div className="dg-resolution-choice__body">
                        <span className="dg-resolution-choice__title">{opt.label}</span>
                        <span className="dg-resolution-choice__desc">{opt.desc}</span>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div className="dg-resolution-note-field">
                <label htmlFor="res-note" className="dg-resolution-label">
                  Resolution Note (Optional context or shift notes):
                </label>
                <textarea
                  id="res-note"
                  className="dg-resolution-textarea"
                  rows={3}
                  value={resolutionNote}
                  onChange={(e) => setResolutionNote(e.target.value)}
                  placeholder="e.g. Guard replacement dispatched from standby squad; site roster reconciled."
                />
              </div>
            </div>

            <footer className="dg-modal__footer">
              <button
                type="button"
                className="dg-btn dg-btn--secondary"
                onClick={() => setResolvingItem(null)}
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                type="button"
                className="dg-btn dg-btn--primary"
                onClick={() => void handleResolveSubmit()}
                disabled={actionLoading}
              >
                {actionLoading ? "Resolving..." : "Confirm Resolution"}
              </button>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
}
