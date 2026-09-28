import { useState } from "react";
import { submitTaskFeedback, type TaskFeedbackRating, type DifficultyReason } from "../../api/support";
import { Modal } from "../../components/Modal";

interface TaskFeedbackModalProps {
  taskId: number;
  taskName: string;
  onClose: () => void;
  onSubmitted?: () => void;
}

const RATINGS: { key: TaskFeedbackRating; label: string }[] = [
  { key: "easy", label: "Easy" },
  { key: "okay", label: "Okay" },
  { key: "difficult", label: "Difficult" },
  { key: "could_not_complete", label: "Couldn't finish it" },
];

const DIFFICULTY_REASONS: { key: DifficultyReason; label: string }[] = [
  { key: "unclear_instructions", label: "The instructions weren't clear" },
  { key: "system_slow_or_buggy", label: "The system was slow or showed an error" },
  { key: "site_conditions", label: "Site access or conditions got in the way" },
  { key: "time_pressure", label: "Not enough time" },
  { key: "missing_equipment", label: "Something I needed was missing" },
  { key: "other", label: "Other" },
];

/**
 * One-tap "how was that?" after submitting a task. It is optional: failures
 * never interrupt the employee, and Skip is always available. The answers
 * show where tasks are hard, which is a training signal, not a performance
 * score.
 */
export function TaskFeedbackModal({ taskId, taskName, onClose, onSubmitted }: TaskFeedbackModalProps) {
  const [rating, setRating] = useState<TaskFeedbackRating | null>(null);
  const [reason, setReason] = useState<DifficultyReason | undefined>(undefined);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const needsDetail = rating === "difficult" || rating === "could_not_complete";

  async function send(r: TaskFeedbackRating, detail?: { difficulty_reason?: DifficultyReason; notes?: string }) {
    setSubmitting(true);
    try {
      await submitTaskFeedback({ task_id: taskId, rating: r, ...detail });
      onSubmitted?.();
    } catch {
      // Micro-feedback must never block the workflow.
    } finally {
      setSubmitting(false);
      onClose();
    }
  }

  function choose(r: TaskFeedbackRating) {
    setRating(r);
    if (r === "easy" || r === "okay") void send(r);
  }

  return (
    <Modal
      title="Done. How was that?"
      subtitle={taskName}
      size="sm"
      onClose={onClose}
      busy={submitting}
      footer={
        needsDetail ? (
          <>
            <button type="button" className="dg-btn" onClick={onClose} disabled={submitting}>Skip</button>
            <button
              type="button"
              className="dg-btn dg-btn--primary"
              disabled={submitting}
              onClick={() => rating && void send(rating, { difficulty_reason: reason, notes: notes.trim() || undefined })}
            >
              {submitting ? "Sending…" : "Send"}
            </button>
          </>
        ) : (
          <button type="button" className="dg-btn dg-btn--ghost" onClick={onClose} disabled={submitting}>Skip</button>
        )
      }
    >
      {!needsDetail ? (
        <div className="dg-chipset">
          {RATINGS.map((r) => (
            <button key={r.key} type="button" className="dg-chip-btn" disabled={submitting} onClick={() => choose(r.key)}>
              {r.label}
            </button>
          ))}
        </div>
      ) : (
        <fieldset className="dg-field" style={{ border: 0, padding: 0 }}>
          <legend className="dg-field__label">
            {rating === "difficult" ? "What made it difficult?" : "What stopped you?"}
          </legend>
          {DIFFICULTY_REASONS.map((r) => (
            <label key={r.key} className="dg-check">
              <input type="radio" name="difficulty_reason" checked={reason === r.key} onChange={() => setReason(r.key)} />
              <span>{r.label}</span>
            </label>
          ))}
          <input
            className="dg-input"
            placeholder="Anything else? (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </fieldset>
      )}
    </Modal>
  );
}
