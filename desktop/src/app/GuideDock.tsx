import { useCallback, useEffect, useState } from "react";
import {
  abandonGuidance, askGuidanceAi, confirmStep, fetchActiveGuidance, requestHelp, showMe,
  type GuidanceAnswer, type GuidanceHelp, type GuidanceSession,
} from "../api/guidance";
import { SafeHtml } from "../components/SafeHtml";
import { ErrorState, Spinner } from "../components/States";
import { WindowControls } from "../shell/Toolbar";
import { CheckCircleIcon, CompassIcon, HelpIcon, SparklesIcon } from "../shell/icons";
import { useViewMode } from "./viewMode";

const POLL_MS = 1500;

/**
 * The guide panel beside Odoo during a guided task.
 *
 * It shows what the server says: the step, why, progress, and whether the
 * employee is off track. The ERP-side runner reports the screen and draws the
 * highlight. This panel only asks: show me, I'm stuck, ask, stop. It never
 * decides a step is done.
 */
export function GuideDock({ onFinished }: { onFinished: () => void }) {
  const { setMode } = useViewMode();
  const [session, setSession] = useState<GuidanceSession | false | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [help, setHelp] = useState<GuidanceHelp | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<GuidanceAnswer | null>(null);
  const [asking, setAsking] = useState(false);
  const [lastCompleted, setLastCompleted] = useState<GuidanceSession | null>(null);

  const refresh = useCallback(async () => {
    try {
      const s = await fetchActiveGuidance();
      setSession(s);
      setError(null);
    } catch (err) {
      setError(err);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), POLL_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  // Help and AI answers belong to one step; a new step starts clean.
  const stepId = session ? (session.step ? session.step.id : 0) : -1;
  useEffect(() => {
    setHelp(null);
    setAnswer(null);
  }, [stepId]);

  // The session disappears from get_active once completed. Remember the last
  // one we saw so the employee gets a clear "done", not an empty panel.
  useEffect(() => {
    if (session) setLastCompleted(session);
  }, [session]);

  const stop = useCallback(async () => {
    await abandonGuidance().catch(() => {});
    setMode("app");
    onFinished();
  }, [setMode, onFinished]);

  const ask = useCallback(async () => {
    if (!question.trim()) return;
    setAsking(true);
    try {
      setAnswer(await askGuidanceAi(question.trim()));
      setQuestion("");
    } catch (err) {
      setError(err);
    } finally {
      setAsking(false);
    }
  }, [question]);

  const finished = session === false && lastCompleted;

  return (
    <aside className="dg-guide" aria-label="DeployGuard guide">
      <header className="dg-guide__head" data-tauri-drag-region>
        <span className="dg-guide__brand" data-tauri-drag-region><CompassIcon size={16} /> Guide</span>
        <WindowControls />
      </header>

      <div className="dg-guide__body">
        {!!error && <ErrorState error={error} fallback="The guide lost contact with the ERP." onRetry={() => void refresh()} />}
        {session === null && <Spinner label="Starting the guide…" />}

        {finished && (
          <div className="dg-guide__done" role="status">
            <CheckCircleIcon size={28} />
            <h2>Done</h2>
            <p>{lastCompleted.flow.objective || `${lastCompleted.flow.name}: complete.`}</p>
            {lastCompleted.task && <p className="dg-field__hint">DeployGuard checked the records. Your task is marked done.</p>}
            <button type="button" className="dg-btn dg-btn--primary" onClick={() => { setMode("app"); onFinished(); }}>
              Back to today
            </button>
          </div>
        )}

        {session === false && !lastCompleted && (
          <div className="dg-guide__done">
            <p>No guided task is running.</p>
            <button type="button" className="dg-btn" onClick={() => { setMode("app"); onFinished(); }}>Back to DeployGuard</button>
          </div>
        )}

        {session && session.step && (
          <>
            <div className="dg-guide__task">
              <div className="dg-guide__flow">{session.flow.name}</div>
              {(session.site || session.date) && (
                <div className="dg-field__hint">{[session.site, session.date].filter(Boolean).join(" · ")}</div>
              )}
              {session.practice && (
                <div className="dg-badge dg-badge--info">Practice: no real task today</div>
              )}
            </div>

            <ol className="dg-guide__steps" aria-label="Steps">
              {session.steps.map((s, i) => (
                <li
                  key={s.title + i}
                  className={`dg-guide__stepdot${s.done ? " is-done" : ""}${session.step && session.step.index === i + 1 ? " is-current" : ""}`}
                  aria-current={session.step && session.step.index === i + 1 ? "step" : undefined}
                >
                  <span className="dg-sr-only">{s.done ? "Done: " : ""}</span>{s.title}
                </li>
              ))}
            </ol>

            <section className={`dg-guide__now${session.off_track ? " is-off-track" : ""}`} aria-live="polite">
              <div className="dg-guide__stepno">Step {session.step.index} of {session.total}</div>
              {session.off_track ? (
                <>
                  <h2 className="dg-guide__title">You're on a different screen</h2>
                  <p>{session.step.deviation_hint || "Go back to where this step happens."}</p>
                </>
              ) : (
                <>
                  <h2 className="dg-guide__title">{session.step.title}</h2>
                  <p className="dg-guide__instruction">{session.step.instruction}</p>
                </>
              )}
              {session.step.why && (
                <p className="dg-guide__why"><strong>Why: </strong>{session.step.why}</p>
              )}
            </section>

            <div className="dg-guide__actions">
              <button type="button" className="dg-btn dg-btn--primary" onClick={() => void showMe().then((s) => s && setSession(s))}>
                Show me
              </button>
              <button type="button" className="dg-btn" onClick={() => void requestHelp().then((h) => h && setHelp(h))}>
                <HelpIcon size={15} /> I'm stuck
              </button>
              {session.step.confirmable && (
                <button type="button" className="dg-btn" onClick={() => void confirmStep().then(setSession).catch(setError)}>
                  I've done this
                </button>
              )}
            </div>
            {session.step.confirmable && (
              <p className="dg-field__hint">Practice mode: DeployGuard can't check this step without a real task, so tell it when you're done.</p>
            )}

            {help && (
              <section className="dg-guide__help" aria-label="Help">
                {help.help_html ? <SafeHtml className="dg-prose" html={help.help_html} /> : <p>There's no extra help written for this step yet.</p>}
                <form className="dg-guide__ask" onSubmit={(e) => { e.preventDefault(); void ask(); }}>
                  <label className="dg-field__label" htmlFor="dg-guide-q">Still stuck? Ask a question</label>
                  <textarea
                    id="dg-guide-q"
                    className="dg-textarea"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="e.g. What do I do if a guard came but left early?"
                    maxLength={500}
                  />
                  <button type="submit" className="dg-btn" disabled={asking || !question.trim()}>
                    {asking ? "Thinking…" : "Ask"}
                  </button>
                </form>
                {answer && (
                  <div className={`dg-guide__answer${answer.ai ? " is-ai" : ""}`}>
                    <div className="dg-guide__answerlabel">
                      {answer.ai ? <><SparklesIcon size={13} /> AI explanation, based on this step's approved instructions</> : "From this step's help"}
                    </div>
                    <p>{answer.answer}</p>
                    {answer.ai && <p className="dg-field__hint">If this doesn't match what you see, trust the ERP and ask your supervisor.</p>}
                  </div>
                )}
              </section>
            )}
          </>
        )}
      </div>

      {session && (
        <footer className="dg-guide__foot">
          <button type="button" className="dg-btn dg-btn--ghost" onClick={() => void stop()}>Stop guiding me</button>
        </footer>
      )}
    </aside>
  );
}
