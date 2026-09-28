import { useCallback, useEffect, useState } from "react";
import { useSession } from "../session/SessionContext";
import { fetchMyToday, fetchTeamToday, type MyToday, type TeamToday, type TodayTask } from "../api/today";
import type { ViewerContext } from "../api/work";
import { cardStatus, nextAction, progress } from "../domain/work/today";
import { Badge, EmptyState, ErrorState } from "../components/States";
import { useViewMode } from "./viewMode";
import { useStartGuidance } from "./useStartGuidance";
import type { AppPage } from "./pages";
import { BookIcon, CompassIcon, HelpIcon, OdooIcon, UsersIcon } from "../shell/icons";

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
}

/**
 * "What do I need to do right now?" Today's work from the roster, each with
 * why it matters and the one next thing to do. No metrics that don't come from
 * records, and no decoration.
 */
export function Home({ reloadSignal, pageAvailable, canGuide, viewer, onGoTo, onOpenTask, onOpenCourse, onReportProblem }: HomeProps) {
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

  return (
    <div className="dg-page-enter dg-today">
      <header className="dg-today__head">
        <h1 className="dg-greeting">{greeting()}, <span>{firstName}</span></h1>
        {hasToday && today && total > 0 && (
          <p className="dg-today__summary" aria-live="polite">
            {done === total ? "Everything on your list today is done." : `${done} of ${total} done today.`}
          </p>
        )}
      </header>

      {isManagerView && team && <TeamSummary team={team} onOpen={() => onGoTo("team")} />}

      {hasToday && (
        <section aria-labelledby="dg-today-title">
          <h2 id="dg-today-title" className="dg-section-title">Your work today</h2>
          {!!error && <ErrorState error={error} fallback="Today's work couldn't be loaded." onRetry={load} />}
          {!error && !today && <div className="dg-skeleton dg-skeleton--card" />}
          {today && today.employee === false && (
            <EmptyState title="Your login isn't linked to an employee yet">
              Ask the GM to link your user to your employee record. Then your work will appear here.
            </EmptyState>
          )}
          {today && today.employee !== false && tasks.length === 0 && (
            <EmptyState title="Nothing to do right now">
              When the roster gives you work, it appears here with what to do and why.
            </EmptyState>
          )}
          <ol className="dg-today__list">
            {tasks.map((task) => (
              <TodayCard
                key={task.id}
                task={task}
                canGuide={canGuide}
                onOpenTask={onOpenTask}
                onOpenCourse={onOpenCourse}
              />
            ))}
          </ol>
        </section>
      )}

      <footer className="dg-appview__footer">
        <button type="button" className="dg-btn dg-btn--secondary" onClick={() => void signOut()}>Sign out</button>
        <button type="button" className="dg-btn dg-btn--ghost" onClick={onReportProblem}>
          <HelpIcon size={16} /> Something not working? Report it
        </button>
      </footer>
    </div>
  );
}

function TodayCard({ task, canGuide, onOpenTask, onOpenCourse }: {
  task: TodayTask;
  canGuide: boolean;
  onOpenTask: (id: number) => void;
  onOpenCourse: (assignmentId: number | false) => void;
}) {
  const { openInOdoo } = useViewMode();
  const guidance = useStartGuidance();
  const status = cardStatus(task);
  const action = nextAction(task, canGuide);
  const title = task.responsibility || task.name;

  const guide = () => task.guidance_flow_code && void guidance.start(task.guidance_flow_code, { taskId: task.id, path: task.odoo_path });

  return (
    <li className={`dg-todaycard dg-todaycard--${status.tone}`}>
      <div className="dg-todaycard__main">
        <div className="dg-todaycard__title">
          <strong>{title}</strong>
          {task.site && <span className="dg-todaycard__site">{task.site}</span>}
        </div>
        <Badge tone={status.tone}>{status.label}</Badge>
        {task.why_it_matters && <p className="dg-todaycard__why"><span className="dg-sr-only">Why: </span>{task.why_it_matters}</p>}
        {task.training && !task.training.done && action === "learn" && (
          <p className="dg-todaycard__learn">
            <BookIcon size={14} /> New to this? Take “{task.training.course_name}” first. It's short, and you can practise with the guide.
          </p>
        )}
        {!!guidance.error && <ErrorState error={guidance.error} fallback="The guide couldn't start." />}
      </div>

      <div className="dg-todaycard__actions">
        {action === "learn" && (
          <>
            <button type="button" className="dg-btn dg-btn--primary" onClick={() => onOpenCourse(task.training ? task.training.assignment_id : false)}>
              <BookIcon size={15} /> Learn this first
            </button>
            {canGuide && task.guidance_flow_code && (
              <button type="button" className="dg-btn" onClick={guide} disabled={guidance.starting}>
                <CompassIcon size={15} /> Guide me
              </button>
            )}
          </>
        )}
        {action === "guide" && (
          <button type="button" className="dg-btn dg-btn--primary" onClick={guide} disabled={guidance.starting}>
            <CompassIcon size={15} /> {guidance.starting ? "Starting…" : "Guide me"}
          </button>
        )}
        {(action === "guide" || action === "open" || action === "learn") && task.odoo_path && (
          <button type="button" className={`dg-btn${action === "open" ? " dg-btn--primary" : " dg-btn--ghost"}`} onClick={() => void openInOdoo(task.odoo_path || undefined)}>
            <OdooIcon size={15} /> {action === "open" ? "Do it in the ERP" : "I know how"}
          </button>
        )}
        <button type="button" className="dg-btn dg-btn--ghost" onClick={() => onOpenTask(task.id)}>
          Details
        </button>
      </div>
    </li>
  );
}

/** The manager's one-glance line: where today's work is stuck. The detail
 * and the records behind every number are on Team Today. */
function TeamSummary({ team, onOpen }: { team: TeamToday; onOpen: () => void }) {
  const count = (k: "expected" | "done" | "overdue" | "could_not_complete") =>
    team.people.reduce((n, p) => n + p[k].length, 0);
  const expected = count("expected");
  if (expected === 0) return null;
  const overdue = count("overdue");
  const blocked = count("could_not_complete");
  return (
    <button type="button" className="dg-teamsummary" onClick={onOpen}>
      <UsersIcon size={18} />
      <span>
        <strong>Team today:</strong> {count("done")} of {expected} tasks done
        {overdue > 0 && <>, <span className="dg-teamsummary__alert">{overdue} overdue</span></>}
        {blocked > 0 && <>, {blocked} couldn't be done</>}.
      </span>
      <span aria-hidden="true">→</span>
    </button>
  );
}
