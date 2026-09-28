import { useState } from "react";
import { getClientDiagnostics } from "../lib/errorCollector";
import { createSupportRequest, type ClientCategory } from "../api/support";
import { Modal } from "../components/Modal";
import { ErrorState } from "../components/States";

interface ProblemReportDialogProps {
  onClose: () => void;
  currentRoute?: string;
  taskContext?: { id: number; name: string };
  onSuccess?: (ticketRef: string) => void;
}

const CATEGORIES: { key: ClientCategory; label: string }[] = [
  { key: "not_working", label: "Not working" },
  { key: "dont_understand", label: "Don't understand" },
  { key: "no_permission", label: "No permission" },
  { key: "cant_find", label: "Can't find" },
  { key: "my_info_wrong", label: "My info is wrong" },
  { key: "slow", label: "System is slow" },
  { key: "other", label: "Other" },
];

/** "Something's wrong" report into security_support (docs/deployguard/34-feedback-and-support.md). */
export function ProblemReportDialog({ onClose, currentRoute = "/home", taskContext, onSuccess }: ProblemReportDialogProps) {
  const [category, setCategory] = useState<ClientCategory>("not_working");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [isUrgent, setIsUrgent] = useState(false);
  const [includeDiagnostics, setIncludeDiagnostics] = useState(true);
  const [showPreview, setShowPreview] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submittedRef, setSubmittedRef] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<unknown>(null);

  const diagnostics = getClientDiagnostics(currentRoute, taskContext);

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    if (!subject.trim()) return;
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
      setSubmitError(err);
    } finally {
      setSubmitting(false);
    }
  }

  if (submittedRef) {
    return (
      <Modal
        title="Report sent"
        size="sm"
        onClose={onClose}
        footer={<button type="button" className="dg-btn dg-btn--primary" onClick={onClose}>Done</button>}
      >
        <p>
          Reference <strong>{submittedRef}</strong>. The operations team has been told and will follow up with you.
        </p>
      </Modal>
    );
  }

  return (
    <Modal
      title="Report a problem"
      subtitle="Tell us what went wrong. Someone will follow up."
      onClose={onClose}
      busy={submitting}
      footer={
        <>
          <button type="button" className="dg-btn" onClick={onClose} disabled={submitting}>Cancel</button>
          <button
            type="submit"
            form="dg-problem-form"
            className="dg-btn dg-btn--primary"
            disabled={submitting || !subject.trim()}
          >
            {submitting ? "Sending…" : "Send report"}
          </button>
        </>
      }
    >
      <form id="dg-problem-form" onSubmit={handleSubmit}>
        {!!submitError && <ErrorState error={submitError} fallback="The report couldn't be sent." />}

        {taskContext && (
          <div className="dg-alert dg-alert--info">About the task: <strong>{taskContext.name}</strong></div>
        )}

        <fieldset className="dg-field" style={{ border: 0, padding: 0 }}>
          <legend className="dg-field__label">What kind of problem is it?</legend>
          <div className="dg-chipset">
            {CATEGORIES.map((c) => (
              <button
                key={c.key}
                type="button"
                aria-pressed={category === c.key}
                className={`dg-chip-btn${category === c.key ? " is-selected" : ""}`}
                onClick={() => setCategory(c.key)}
              >
                {c.label}
              </button>
            ))}
          </div>
        </fieldset>

        <label className="dg-field">
          <span className="dg-field__label">Summary <span className="dg-required">*</span></span>
          <input
            className="dg-input"
            placeholder="e.g. I can't capture today's attendance for Main Gate"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            required
          />
        </label>

        <label className="dg-field">
          <span className="dg-field__label">Details (optional)</span>
          <textarea
            className="dg-textarea"
            placeholder="What happened, and what did you expect?"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>

        <label className="dg-check dg-field">
          <input type="checkbox" checked={isUrgent} onChange={(e) => setIsUrgent(e.target.checked)} />
          <span><strong>Urgent:</strong> I can't do my work right now</span>
        </label>

        <div className="dg-field">
          <label className="dg-check">
            <input type="checkbox" checked={includeDiagnostics} onChange={(e) => setIncludeDiagnostics(e.target.checked)} />
            <span>Attach technical details (screen, app version, recent errors, with passwords and sessions removed)</span>
          </label>
          <button type="button" className="dg-btn dg-btn--link" onClick={() => setShowPreview((v) => !v)}>
            {showPreview ? "Hide details" : "See exactly what is sent"}
          </button>
          {showPreview && <pre className="dg-pre">{JSON.stringify(diagnostics, null, 2)}</pre>}
        </div>
      </form>
    </Modal>
  );
}
