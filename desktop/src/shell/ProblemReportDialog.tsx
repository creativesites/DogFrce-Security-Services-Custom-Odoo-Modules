import { useState, useId } from "react";
import { getClientDiagnostics, type ClientDiagnostics } from "../lib/errorCollector";
import { createSupportRequest, type ClientCategory } from "../api/support";

interface ProblemReportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  currentRoute?: string;
  taskContext?: { id: number; name: string };
  onSuccess?: (ticketRef: string) => void;
}

const CATEGORIES: { key: ClientCategory; label: string; desc: string }[] = [
  { key: "not_working", label: "Not working", desc: "Something crashed or gave an error" },
  { key: "dont_understand", label: "Don't understand", desc: "Unclear instructions or what to do next" },
  { key: "no_permission", label: "No permission", desc: "Access denied or missing rights" },
  { key: "cant_find", label: "Can't find", desc: "Can't find a guard, site, task, or button" },
  { key: "my_info_wrong", label: "My info is wrong", desc: "Roster, site, or profile details incorrect" },
  { key: "slow", label: "System is slow", desc: "Spinning loaders or long delay" },
  { key: "other", label: "Other", desc: "General enquiry or issue" },
];

export function ProblemReportDialog({
  isOpen,
  onClose,
  currentRoute = "/home",
  taskContext,
  onSuccess,
}: ProblemReportDialogProps) {
  const [category, setCategory] = useState<ClientCategory>("not_working");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [isUrgent, setIsUrgent] = useState(false);
  const [includeDiagnostics, setIncludeDiagnostics] = useState(true);
  const [showDiagnosticsPreview, setShowDiagnosticsPreview] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submittedRef, setSubmittedRef] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const titleId = useId();

  if (!isOpen) return null;

  const diagnostics: ClientDiagnostics = getClientDiagnostics(currentRoute, taskContext);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!subject.trim()) {
      setSubmitError("Please provide a short summary of the issue.");
      return;
    }

    setSubmitting(true);
    setSubmitError(null);

    try {
      const res = await createSupportRequest({
        subject: subject.trim(),
        client_category: category,
        priority: isUrgent ? "3" : "1",
        route: currentRoute,
        work_task_id: taskContext?.id,
        description: description.trim(),
        diagnostics: includeDiagnostics ? diagnostics : undefined,
      });

      setSubmittedRef(res.name);
      onSuccess?.(res.name);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  function handleResetAndClose() {
    setSubmittedRef(null);
    setSubject("");
    setDescription("");
    setIsUrgent(false);
    setSubmitError(null);
    onClose();
  }

  return (
    <div className="dg-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby={titleId}>
      <div className="dg-modal" style={{ maxWidth: 580 }}>
        {submittedRef ? (
          <div className="dg-modal__body" style={{ textAlign: "center", padding: "32px 16px" }}>
            <div style={{ fontSize: 42, marginBottom: 12 }}>✓</div>
            <h2 id={titleId} style={{ margin: "0 0 8px 0" }}>Report Submitted</h2>
            <p style={{ color: "var(--dg-text-secondary, #64748b)", margin: "0 0 16px 0" }}>
              Reference <strong>{submittedRef}</strong> has been logged. Our operations team and support have been notified.
            </p>
            <button
              type="button"
              className="dg-btn dg-btn--primary"
              onClick={handleResetAndClose}
            >
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="dg-modal__head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 20px", borderBottom: "1px solid var(--dg-border, #e2e8f0)" }}>
              <h2 id={titleId} style={{ margin: 0, fontSize: "1.15rem", fontWeight: 600 }}>Report a Problem / Something's Wrong</h2>
              <button
                type="button"
                className="dg-btn dg-btn--secondary"
                style={{ padding: "4px 8px" }}
                onClick={handleResetAndClose}
                disabled={submitting}
              >
                ✕
              </button>
            </div>

            <div className="dg-modal__body" style={{ padding: "20px", maxHeight: "75vh", overflowY: "auto" }}>
              {submitError && (
                <div style={{ background: "#fef2f2", color: "#991b1b", padding: "10px 14px", borderRadius: 6, marginBottom: 16, fontSize: "0.9rem" }}>
                  {submitError}
                </div>
              )}

              {taskContext && (
                <div style={{ background: "var(--dg-bg-muted, #f1f5f9)", padding: "8px 12px", borderRadius: 6, marginBottom: 16, fontSize: "0.85rem" }}>
                  Active task: <strong>{taskContext.name}</strong> (ID #{taskContext.id})
                </div>
              )}

              {/* Category Chips */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: 8 }}>
                  What kind of issue are you experiencing?
                </label>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {CATEGORIES.map((c) => (
                    <button
                      key={c.key}
                      type="button"
                      className={`dg-chip-btn ${category === c.key ? "is-selected" : ""}`}
                      style={{
                        padding: "6px 12px",
                        borderRadius: 16,
                        border: "1px solid",
                        borderColor: category === c.key ? "var(--dg-primary, #1a3a5c)" : "var(--dg-border, #cbd5e1)",
                        background: category === c.key ? "var(--dg-primary, #1a3a5c)" : "transparent",
                        color: category === c.key ? "#ffffff" : "inherit",
                        fontSize: "0.85rem",
                        cursor: "pointer",
                      }}
                      onClick={() => setCategory(c.key)}
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Subject */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: 6 }}>
                  Summary <span style={{ color: "#e11d48" }}>*</span>
                </label>
                <input
                  type="text"
                  className="dg-input"
                  style={{ width: "100%", padding: "8px 12px", borderRadius: 6, border: "1px solid var(--dg-border, #cbd5e1)" }}
                  placeholder="e.g. Cannot complete checklist item #3 or submit attendance"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  required
                />
              </div>

              {/* Description */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: 6 }}>
                  Details (optional)
                </label>
                <textarea
                  className="dg-textarea"
                  style={{ width: "100%", minHeight: 80, padding: "8px 12px", borderRadius: 6, border: "1px solid var(--dg-border, #cbd5e1)" }}
                  placeholder="Tell us what happened, what you expected, or any steps to reproduce..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              {/* Priority Checkbox */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.88rem", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={isUrgent}
                    onChange={(e) => setIsUrgent(e.target.checked)}
                  />
                  <span>
                    <strong>Urgent / Blocking</strong> — I cannot perform my duty or shift right now
                  </span>
                </label>
              </div>

              {/* Diagnostics & Redaction (docs/deployguard/34-feedback-and-support.md §1.3) */}
              <div style={{ borderTop: "1px solid var(--dg-border, #e2e8f0)", paddingTop: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.85rem", cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={includeDiagnostics}
                      onChange={(e) => setIncludeDiagnostics(e.target.checked)}
                    />
                    <span>Attach system diagnostics (route, app version, error buffer)</span>
                  </label>
                  <button
                    type="button"
                    style={{ background: "none", border: "none", color: "var(--dg-primary, #1a3a5c)", fontSize: "0.8rem", cursor: "pointer", textDecoration: "underline" }}
                    onClick={() => setShowDiagnosticsPreview(!showDiagnosticsPreview)}
                  >
                    {showDiagnosticsPreview ? "Hide details" : "Inspect details"}
                  </button>
                </div>

                {showDiagnosticsPreview && (
                  <pre
                    style={{
                      marginTop: 10,
                      padding: 10,
                      background: "#0f172a",
                      color: "#94a3b8",
                      borderRadius: 6,
                      fontSize: "0.75rem",
                      maxHeight: 140,
                      overflow: "auto",
                    }}
                  >
                    {JSON.stringify(diagnostics, null, 2)}
                  </pre>
                )}
              </div>
            </div>

            <div className="dg-modal__foot" style={{ display: "flex", justifyContent: "flex-end", gap: 10, padding: "14px 20px", borderTop: "1px solid var(--dg-border, #e2e8f0)", background: "var(--dg-bg-subtle, #f8fafc)" }}>
              <button
                type="button"
                className="dg-btn dg-btn--secondary"
                onClick={handleResetAndClose}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="dg-btn dg-btn--primary"
                disabled={submitting || !subject.trim()}
              >
                {submitting ? "Submitting..." : "Send Problem Report"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
