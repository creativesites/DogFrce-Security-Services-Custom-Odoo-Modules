import { useCallback, useEffect, useState } from "react";
import { useSession } from "../session/SessionContext";
import { fetchMyToday, fetchTeamToday, type MyToday, type TeamToday, type TodayTask } from "../api/today";
import type { ViewerContext } from "../api/work";
import { arrangeDay, cardStatus, daySentence, dueTime, nextAction, progress, titleAndSite } from "../domain/work/today";
import { EmptyState, ErrorState } from "../components/States";
import { Ramp } from "../components/Ramp";
import { useViewMode } from "./viewMode";
import { useStartGuidance } from "./useStartGuidance";
import type { AppPage } from "./pages";
import { BookIcon, CheckCircleIcon, CompassIcon, HelpIcon, LifeBuoyIcon, OdooIcon, UsersIcon } from "../shell/icons";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

interface HomeProps {
  reloadSignal: number;
  pageAvailable: (p: AppPage) => boolean;
  canGuide: boolean;
  viewer: ViewerContext | null;
  onGoTo: (p: AppPage) => void;
  onOpenTask: (taskId: number) => void;
  onOpenCourse: (assignmentId: number | false) => void;
  onReportProblem: () => void;
  onHelp?: () => void;
}

/**
 * Today: "What do I need to do right now?"
 * One focus card (Up next), then the rest of the day in time order, then
 * what's done. Every fact comes from the server's Today API.
 */
export function Home({ reloadSignal, pageAvailable, canGuide, viewer, onGoTo, onOpenTask, onOpenCourse, onReportProblem, onHelp }: HomeProps) {
  const { session, signOut } = useSession();
  const hasToday = pageAvailable("work");
  const [today, setToday] = useState<MyToday | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [team, setTeam] = useState<TeamToday | null>(null);
  const isManagerView = !!viewer && (viewer.is_supervisor || viewer.is_manager || viewer.is_owner) && pageAvailable("team");

  const load = useCallback(() => {
    if (!hasToday) return;
    setError(null);
    fetchMyToday().then(setToday).catch(setError);
    if (isManagerView) fetchTeamToday().then(setTeam).catch(() => setTeam(null));
  }, [hasToday, isManagerView]);

  useEffect(() => { load(); }, [load, reloadSignal]);

  if (!session) return null;
  const firstName = session.name.split(" ")[0];
  const tasks = today?.tasks ?? [];
  const { done, total } = progress(tasks);
  const day = arrangeDay(tasks, canGuide);
  const learning = tasks.find((t) => t.training && !t.training.done)?.training || null;
  const dateLine = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });

  return (
    <div className="dg-today dg-page-enter">
      <header className="dg-hero">
        <div className="dg-hero__text">
          <p className="dg-eyebrow">{dateLine}</p>
          <h1 className="dg-display">{greeting()}, <span className="dg-hero__name">{firstName}</span></h1>
          {hasToday && today && today.employee !== false && <p className="dg-subline">{daySentence(tasks)}</p>}
        </div>
        {hasToday && total > 0 && <ProgressRing done={done} total={total} />}
      </header>

      {isManagerView && team && <TeamSummary team={team} onOpen={() => onGoTo("team")} />}

      {hasToday && (
        <div className="dg-today__grid">
          <div className="dg-today__main">
            {!!error && <ErrorState error={error} fallback="Today's work couldn't be loaded." onRetry={load} />}
            {!error && !today && <div className="dg-skeleton dg-upnext-skeleton" />}
            {today && today.employee === false && (
              <EmptyState title="Your login isn't linked to an employee yet">
                Ask the GM to link your user to your employee record. Then your work will appear here.
              </EmptyState>
            )}
            {today && today.employee !== false && tasks.length === 0 && (
              <div className="dg-panel dg-calm">
                <CheckCircleIcon size={28} />
                <div>
                  <h2>Nothing to do right now</h2>
                  <p>When the roster gives you work, it appears here with what to do and why.</p>
                </div>
              </div>
            )}

            {day.upNext && (
              <UpNext task={day.upNext} canGuide={canGuide} onOpenTask={onOpenTask} onOpenCourse={onOpenCourse} />
            )}

            {day.later.length > 0 && (
              <section aria-labelledby="dg-later" className="dg-daysection">
                <h2 id="dg-later" className="dg-section-title">{day.upNext ? "Then" : "Your work today"}</h2>
                <ol className="dg-timeline">
                  {day.later.map((t) => <TimelineRow key={t.id} task={t} canGuide={canGuide} onOpenTask={onOpenTask} />)}
                </ol>
              </section>
            )}

            {day.done.length > 0 && (
              <section aria-labelledby="dg-done" className="dg-daysection">
                <h2 id="dg-done" className="dg-section-title">Done today</h2>
                <ul className="dg-donelist">
                  {day.done.map((t) => (
                    <li key={t.id}>
                      <button type="button" className="dg-donelist__row" onClick={() => onOpenTask(t.id)}>
                        <span className={`dg-donelist__tick${t.state === "could_not_complete" ? " is-cnc" : ""}`} aria-hidden="true">
                          {t.state === "could_not_complete" ? "!" : <CheckCircleIcon size={16} />}
                        </span>
                        <span className="dg-donelist__name">{titleAndSite(t).title}</span>
                        {titleAndSite(t).site && <span className="dg-donelist__site">{titleAndSite(t).site}</span>}
                        <span className="dg-donelist__state">{cardStatus(t).label}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>

          <aside className="dg-today__aside" aria-label="Help and learning">
            {learning && (
              <div className="dg-panel dg-learncard">
                <div className="dg-learncard__icon"><BookIcon size={18} /></div>
                <h2 className="dg-panel__title">Learn this first</h2>
                <p>{learning.course_name}</p>
                <p className="dg-field__hint">Short lessons, then practise in the real ERP with the guide beside you.</p>
                <button type="button" className="dg-btn dg-btn--primary" onClick={() => onOpenCourse(learning.assignment_id)}>
                  Start the course
                </button>
              </div>
            )}
            <div className="dg-panel dg-helpcard">
              <h2 className="dg-panel__title">Need a hand?</h2>
              <button type="button" className="dg-helpcard__row" onClick={onHelp}>
                <HelpIcon size={17} /> <span>How do I…?</span>
              </button>
              <button type="button" className="dg-helpcard__row" onClick={onReportProblem}>
                <LifeBuoyIcon size={17} /> <span>Something isn't working</span>
              </button>
              <button type="button" className="dg-helpcard__row dg-helpcard__row--quiet" onClick={() => void signOut()}>
                <span>Sign out</span>
              </button>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

function ProgressRing({ done, total }: { done: number; total: number }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const pct = total ? done / total : 0;
  const complete = done === total;
  return (
    <div className={`dg-ring${complete ? " is-complete" : ""}`} role="img" aria-label={`${done} of ${total} done today`}>
      <svg viewBox="0 0 84 84" width="84" height="84" aria-hidden="true">
        <circle className="dg-ring__track" cx="42" cy="42" r={r} />
        <circle className="dg-ring__value" cx="42" cy="42" r={r} strokeDasharray={c} strokeDashoffset={c * (1 - pct)} />
      </svg>
      <div className="dg-ring__text">
        <span className="dg-ring__num dg-num">{done}<span>/{total}</span></span>
        <span className="dg-ring__cap">done</span>
      </div>
    </div>
  );
}

/** The one thing to do now. Dark ink, like the shell's rail: it's the focus. */
function UpNext({ task, canGuide, onOpenTask, onOpenCourse }: {
  task: TodayTask;
  canGuide: boolean;
  onOpenTask: (id: number) => void;
  onOpenCourse: (assignmentId: number | false) => void;
}) {
  const { openInOdoo } = useViewMode();
  const guidance = useStartGuidance();
  const status = cardStatus(task);
  const action = nextAction(task, canGuide);
  const guide = () => task.guidance_flow_code && void guidance.start(task.guidance_flow_code, { taskId: task.id, path: task.odoo_path });
  const { title, site } = titleAndSite(task);

  return (
    <section className={`dg-upnext${task.is_overdue ? " is-overdue" : ""}`} aria-labelledby="dg-upnext-title">
      <div className="dg-upnext__top">
        <span className="dg-upnext__label">Up next</span>
        <span className={`dg-upnext__status dg-upnext__status--${status.tone}`}>{status.label}</span>
      </div>
      <h2 id="dg-upnext-title" className="dg-upnext__title">
        {title}
        {site && <span className="dg-upnext__site">{site}</span>}
      </h2>
      {task.why_it_matters && (
        <p className="dg-upnext__why"><span className="dg-upnext__whylabel">Why it matters</span>{task.why_it_matters}</p>
      )}
      {!!guidance.error && <ErrorState error={guidance.error} fallback="The guide couldn't start." />}
      <div className="dg-upnext__actions">
        {action === "learn" && (
          <button type="button" className="dg-upnext__primary" onClick={() => onOpenCourse(task.training ? task.training.assignment_id : false)}>
            <BookIcon size={17} /> Learn this first
          </button>
        )}
        {(action === "guide" || (action === "learn" && canGuide && task.guidance_flow_code)) && (
          <button type="button" className={action === "guide" ? "dg-upnext__primary" : "dg-upnext__secondary"} onClick={guide} disabled={guidance.starting}>
            <CompassIcon size={17} /> {guidance.starting ? "Starting…" : "Guide me"}
          </button>
        )}
        {task.odoo_path && (
          <button type="button" className={action === "open" ? "dg-upnext__primary" : "dg-upnext__secondary"} onClick={() => void openInOdoo(task.odoo_path || undefined)}>
            <OdooIcon size={16} /> {action === "open" ? "Do it in the ERP" : "I know how"}
          </button>
        )}
        <button type="button" className="dg-upnext__link" onClick={() => onOpenTask(task.id)}>Details</button>
      </div>
    </section>
  );
}

function TimelineRow({ task, canGuide, onOpenTask }: { task: TodayTask; canGuide: boolean; onOpenTask: (id: number) => void }) {
  const guidance = useStartGuidance();
  const status = cardStatus(task);
  const action = nextAction(task, canGuide);
  const time = dueTime(task);
  const { title, site } = titleAndSite(task);
  return (
    <li className={`dg-timeline__row dg-timeline__row--${status.tone}`}>
      <span className="dg-timeline__time dg-num">{time ?? "Today"}</span>
      <span className="dg-timeline__dot" aria-hidden="true" />
      <div className="dg-timeline__card">
        <div className="dg-timeline__head">
          <strong>{title}</strong>
          {site && <span className="dg-timeline__site">{site}</span>}
        </div>
        <span className={`dg-chip-state dg-chip-state--${status.tone}`}>{status.label}</span>
        <div className="dg-timeline__actions">
          {action === "guide" && task.guidance_flow_code && (
            <button type="button" className="dg-btn dg-btn--sm" disabled={guidance.starting}
              onClick={() => void guidance.start(task.guidance_flow_code as string, { taskId: task.id, path: task.odoo_path })}>
              <CompassIcon size={14} /> Guide me
            </button>
          )}
          <button type="button" className="dg-btn dg-btn--sm dg-btn--ghost" onClick={() => onOpenTask(task.id)}>Details</button>
        </div>
      </div>
    </li>
  );
}

/** The manager's one-glance line: where today's work stands. */
function TeamSummary({ team, onOpen }: { team: TeamToday; onOpen: () => void }) {
  const count = (k: "expected" | "done" | "overdue" | "could_not_complete") =>
    team.people.reduce((n, p) => n + p[k].length, 0);
  const expected = count("expected");
  if (expected === 0) return null;
  const doneN = count("done");
  const overdue = count("overdue");
  const blocked = count("could_not_complete");
  return (
    <button type="button" className="dg-teamstrip" onClick={onOpen}>
      <span className="dg-teamstrip__icon"><UsersIcon size={18} /></span>
      <span className="dg-teamstrip__main">
        <span className="dg-teamstrip__title">Team today</span>
        <Ramp value={doneN} max={expected} />
      </span>
      <span className="dg-teamstrip__stat"><b className="dg-num">{doneN}/{expected}</b> done</span>
      {overdue > 0 && <span className="dg-teamstrip__stat is-danger"><b className="dg-num">{overdue}</b> overdue</span>}
      {blocked > 0 && <span className="dg-teamstrip__stat"><b className="dg-num">{blocked}</b> couldn't be done</span>}
      <span className="dg-teamstrip__go" aria-hidden="true">→</span>
    </button>
  );
}
