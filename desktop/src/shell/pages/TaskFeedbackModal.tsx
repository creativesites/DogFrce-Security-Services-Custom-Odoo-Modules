import { useState } from "react";
import { submitTaskFeedback, type TaskFeedbackRating, type DifficultyReason } from "../../api/support";

interface TaskFeedbackModalProps {
  isOpen: boolean;
  taskId: number;
  taskName: string;
  onClose: () => void;
  onSubmitted?: () => void;
}

const DIFFICULTY_REASONS: { key: DifficultyReason; label: string }[] = [
  { key: "unclear_instructions", label: "Unclear instructions or template wording" },
  { key: "system_slow_or_buggy", label: "System was slow or encountered an error" },
  { key: "site_conditions", label: "Site access blocked or poor lighting/conditions" },
  { key: "time_pressure", label: "Not enough time scheduled for this task" },
  { key: "missing_equipment", label: "Missing torch, radio, or keys" },
  { key: "other", label: "Other" },
];

export function TaskFeedbackModal({
  isOpen,
  taskId,
  taskName,
  onClose,
  onSubmitted,
}: TaskFeedbackModalProps) {
  const [rating, setRating] = useState<TaskFeedbackRating | null>(null);
  const [reason, setReason] = useState<DifficultyReason | undefined>(undefined);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSelectRating(r: TaskFeedbackRating) {
    setRating(r);
    // For easy or okay, we can submit immediately with one tap!
    if (r === "easy" || r === "okay") {
      setSubmitting(true);
      try {
        await submitTaskFeedback({ task_id: taskId, rating: r });
        onSubmitted?.();
        onClose();
      } catch {
        // Non-blocking micro-feedback — do not disrupt workflow on failure
        onClose();
      } finally {
        setSubmitting(false);
      }
    }
  }

  async function handleDetailedSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!rating) return;
    setSubmitting(true);
    try {
      await submitTaskFeedback({
        task_id: taskId,
        rating,
        difficulty_reason: reason,
        notes: notes.trim() || undefined,
      });
      onSubmitted?.();
      onClose();
    } catch {
      onClose();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="dg-modal-backdrop" role="dialog" aria-modal="true" aria-label="Task Feedback">
      <div className="dg-modal" style={{ maxWidth: 440, padding: 24, textAlign: "center" }}>
        <h3 style={{ margin: "0 0 4px 0", fontSize: "1.1rem", fontWeight: 600 }}>Task Completed</h3>
        <p style={{ margin: "0 0 16px 0", fontSize: "0.85rem", color: "var(--dg-text-secondary, #64748b)" }}>
          {taskName}
        </p>

        {!rating || (rating !== "difficult" && rating !== "could_not_complete") ? (
          <div>
            <div style={{ fontSize: "1rem", fontWeight: 500, marginBottom: 16 }}>How was that?</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 16 }}>
              <button
                type="button"
                className="dg-btn dg-btn--secondary"
                style={{ padding: "14px 10px", fontSize: "0.95rem" }}
                onClick={() => handleSelectRating("easy")}
                disabled={submitting}
              >
                😊 Easy
              </button>
              <button
                type="button"
                className="dg-btn dg-btn--secondary"
                style={{ padding: "14px 10px", fontSize: "0.95rem" }}
                onClick={() => handleSelectRating("okay")}
                disabled={submitting}
              >
                😐 Okay
              </button>
              <button
                type="button"
                className="dg-btn dg-btn--secondary"
                style={{ padding: "14px 10px", fontSize: "0.95rem" }}
                onClick={() => handleSelectRating("difficult")}
                disabled={submitting}
              >
                😓 Difficult
              </button>
              <button
                type="button"
                className="dg-btn dg-btn--secondary"
                style={{ padding: "14px 10px", fontSize: "0.95rem" }}
                onClick={() => handleSelectRating("could_not_complete")}
                disabled={submitting}
              >
                🚫 Couldn't complete
              </button>
            </div>
            <button
              type="button"
              style={{ background: "none", border: "none", color: "#64748b", fontSize: "0.82rem", cursor: "pointer" }}
              onClick={onClose}
              disabled={submitting}
            >
              Skip
            </button>
          </div>
        ) : (
          <form onSubmit={handleDetailedSubmit} style={{ textAlign: "left" }}>
            <div style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: 8 }}>
              {rating === "difficult" ? "What made it difficult?" : "What prevented completion?"}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 14 }}>
              {DIFFICULTY_REASONS.map((r) => (
                <label
                  key={r.key}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    fontSize: "0.85rem",
                    cursor: "pointer",
                    padding: "4px 0",
                  }}
                >
                  <input
                    type="radio"
                    name="difficulty_reason"
                    checked={reason === r.key}
                    onChange={() => setReason(r.key)}
                  />
                  <span>{r.label}</span>
                </label>
              ))}
            </div>

            <div style={{ marginBottom: 16 }}>
              <input
                type="text"
                className="dg-input"
                placeholder="Optional comments..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                style={{ width: "100%", padding: "8px 10px", fontSize: "0.85rem", borderRadius: 6 }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button
                type="button"
                className="dg-btn dg-btn--secondary"
                onClick={onClose}
                disabled={submitting}
              >
                Skip
              </button>
              <button
                type="submit"
                className="dg-btn dg-btn--primary"
                disabled={submitting}
              >
                {submitting ? "Sending..." : "Send Feedback"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
