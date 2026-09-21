import { useState } from "react";
import type { NoticeStatus } from "../api/onboarding";
import { extractErrorMessage } from "../lib/extractErrorMessage";
import { BookIcon, ClipboardListIcon, LifeBuoyIcon, ShieldCheckIcon } from "./icons";

type Step = "welcome" | "notice" | "ready";

interface Props {
  firstName: string;
  status: NoticeStatus;
  /** Records the acknowledgement server-side; rejects with a user-facing message. */
  onAcknowledge: () => Promise<void>;
  onFinish: (page: "training" | "work") => void;
}

/**
 * What a new employee sees the first time they sign in: what the app is
 * for, the monitoring notice (16-security-architecture §9 -- acknowledged,
 * recorded on the server, no way past it without reading it), then a
 * single obvious next step into their training.
 */
export function FirstRunOnboarding({ firstName, status, onAcknowledge, onFinish }: Props) {
  const needsNotice = status.kind === "needs_ack";
  const [step, setStep] = useState<Step>("welcome");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const steps: Step[] = needsNotice ? ["welcome", "notice", "ready"] : ["welcome", "ready"];
  const position = steps.indexOf(step) + 1;

  async function acknowledge() {
    setSaving(true);
    setError(null);
    try {
      await onAcknowledge();
      setStep("ready");
    } catch (err) {
      setError(extractErrorMessage(err, "Couldn't record that. Check your connection and try again."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="dg-onboarding dg-page-enter" role="region" aria-label="Getting started">
      <p className="dg-onboarding__step" aria-live="polite">
        Step {position} of {steps.length}
      </p>

      {step === "welcome" && (
        <>
          <h1 className="dg-greeting">
            Welcome to DogForce, <span>{firstName}</span>
          </h1>
          <p className="dg-onboarding__lead">This app is where you'll do three things:</p>
          <ul className="dg-onboarding__list">
            <li>
              <span className="dg-onboarding__icon"><ClipboardListIcon size={18} /></span>
              <span><strong>My Work &amp; Sweeps</strong>: the tasks and checklists assigned to you.</span>
            </li>
            <li>
              <span className="dg-onboarding__icon"><BookIcon size={18} /></span>
              <span><strong>My Training</strong>: short courses that teach you the system, at your own pace.</span>
            </li>
            <li>
              <span className="dg-onboarding__icon"><LifeBuoyIcon size={18} /></span>
              <span><strong>Report a problem</strong>: if something's wrong, tell us from inside the app.</span>
            </li>
          </ul>
          <div className="dg-onboarding__actions">
            <button type="button" className="dg-btn dg-btn--primary" onClick={() => setStep(needsNotice ? "notice" : "ready")}>
              Continue
            </button>
          </div>
        </>
      )}

      {step === "notice" && status.kind === "needs_ack" && (
        <>
          <h1 className="dg-onboarding__title">
            <span className="dg-onboarding__icon"><ShieldCheckIcon size={20} /></span>
            {status.notice.title}
          </h1>
          <div className="dg-card dg-onboarding__notice">
            {status.notice.body.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </div>
          {error && (
            <p className="dg-onboarding__error" role="alert">{error}</p>
          )}
          <div className="dg-onboarding__actions">
            <button type="button" className="dg-btn dg-btn--primary" onClick={() => void acknowledge()} disabled={saving}>
              {saving ? "Saving…" : "I've read and understand this"}
            </button>
          </div>
          <p className="dg-onboarding__fineprint">Notice version {status.notice.version}</p>
        </>
      )}

      {step === "ready" && (
        <>
          <h1 className="dg-greeting">You're all set, <span>{firstName}</span></h1>
          <p className="dg-onboarding__lead">
            The best place to start is your training. It walks you through the system step by step,
            and you can try each step for real as you go.
          </p>
          <div className="dg-onboarding__actions">
            <button type="button" className="dg-btn dg-btn--primary" onClick={() => onFinish("training")}>
              <BookIcon size={16} /> Start my training
            </button>
            <button type="button" className="dg-btn dg-btn--secondary" onClick={() => onFinish("work")}>
              Go to My Work
            </button>
          </div>
        </>
      )}
    </div>
  );
}
