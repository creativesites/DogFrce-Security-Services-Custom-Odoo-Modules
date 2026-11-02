import { useCallback, useState } from "react";
import { fetchTasksByIds, fetchTeamToday, type TeamCell, type TeamPerson, type TeamToday as TeamTodayData } from "../../api/today";
import { EvidenceModal } from "../../components/EvidenceModal";
import { EmptyState, ErrorState } from "../../components/States";
import { TeamTodaySkeleton } from "../../components/Skeletons";
import { Ramp } from "../../components/Ramp";
import { AttentionCard, type AttentionItem } from "../../components/AttentionCard";
import { useQuery } from "../../lib/queryCache";
import { useViewMode } from "../../app/viewMode";

const TASK_PATH = "/odoo/action-security_work.action_security_work_task";
const EVIDENCE_FIELDS = ["name", "employee_id", "site_id", "due_at", "state", "cnc_reason", "cnc_note"];

type Tone = "done" | "doing" | "todo" | "overdue" | "waiting" | "blocked" | "none";

function cellView(cell: TeamCell | undefined): { label: string; tone: Tone } {
  if (!cell) return { label: "Not expected", tone: "none" };
  if (cell.state === "verified") return { label: "Done, checked", tone: "done" };
  if (cell.state === "submitted") return { label: "Done", tone: "done" };
  if (cell.state === "could_not_complete") return { label: "Couldn't do", tone: "blocked" };
  if (cell.is_overdue) return { label: "Overdue", tone: "overdue" };
  if (cell.readiness === "waiting") return { label: "Waiting", tone: "waiting" };
  if (cell.state === "in_progress") return { label: "In progress", tone: "doing" };
  return { label: "To do", tone: "todo" };
}

function initials(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("");
}

const sum = (people: TeamPerson[], k: keyof Pick<TeamPerson, "expected" | "done" | "overdue" | "could_not_complete" | "waiting">) =>
  people.flatMap((p) => p[k]);

/**
 * The GM's "where is it stuck?" view. Each site's pipeline as a track of real
 * tasks, then each person's day. Every number and node opens the records
 * behind it. Nothing here is a score.
 */
export function TeamToday({ reloadSignal }: { reloadSignal?: number }) {
  const { openInOdoo } = useViewMode();
  const [evidence, setEvidence] = useState<{ title: string; ids: number[] } | null>(null);

  const {
    data,
    error,
    isLoading,
    refetch,
  } = useQuery<TeamTodayData>(
    "today:team",
    fetchTeamToday,
    { reloadSignal, staleTime: 20_000 },
  );

  const loadEvidence = useCallback(() => fetchTasksByIds(evidence?.ids ?? []), [evidence]);

  if (error) return <ErrorState error={error} fallback="Team Today couldn't be loaded." onRetry={() => void refetch()} />;
  if (isLoading && !data) return <TeamTodaySkeleton />;
  if (!data) return <TeamTodaySkeleton />;

  const openTask = (id: number) => void openInOdoo(`${TASK_PATH}/${id}`);
  const expected = sum(data.people, "expected");
  const done = sum(data.people, "done");
  const overdue = sum(data.people, "overdue");
  const waiting = sum(data.people, "waiting");
  const blocked = sum(data.people, "could_not_complete");
  const dateLine = new Date(`${data.date}T12:00:00`).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });

  const attentionItems: AttentionItem[] = [];
  if (overdue.length > 0) {
    attentionItems.push({
      id: "overdue",
      tone: "danger",
      title: `${overdue.length} overdue ${overdue.length === 1 ? "duty requires" : "duties require"} attention`,
      detail: "Pending duties have passed their operational deadline. Follow up with site supervisors.",
      actionLabel: "Inspect overdue",
      onAction: () => setEvidence({ title: "Overdue duties today", ids: overdue }),
    });
  }
  if (blocked.length > 0) {
    attentionItems.push({
      id: "blocked",
      tone: "warning",
      title: `${blocked.length} ${blocked.length === 1 ? "duty" : "duties"} couldn't be completed`,
      detail: "Guard reported obstruction, post lockouts, or safety risks requiring review.",
      actionLabel: "Review reasons",
      onAction: () => setEvidence({ title: "Couldn't complete duties", ids: blocked }),
    });
  }
  if (waiting.length > 0) {
    attentionItems.push({
      id: "waiting",
      tone: "info",
      title: `${waiting.length} ${waiting.length === 1 ? "duty" : "duties"} waiting on handoff`,
      detail: "Awaiting preceding shift sign-off or relief officer arrival.",
      actionLabel: "View waiting",
      onAction: () => setEvidence({ title: "Waiting on someone", ids: waiting }),
    });
  }

  return (
    <div className="dg-team dg-page-enter">
      <header className="dg-hero">
        <div className="dg-hero__text">
          <p className="dg-eyebrow">{dateLine}</p>
          <h1 className="dg-display">Team today</h1>
          <p className="dg-subline">Where each site's work has got to, and who has it. Everything opens the records behind it.</p>
        </div>
      </header>

      {expected.length === 0 ? (
        <EmptyState title="No work is expected today">
          Tasks appear here once the roster has guards at sites and duties have owners (Work → Set up attendance pipeline).
        </EmptyState>
      ) : (
        <>
          <AttentionCard
            title="Today's Attention"
            subtitle="Operational priorities and bottlenecks synthesized across active sites and guard shifts"
            badge="Manager Attention"
            items={attentionItems}
            emptyMessage="All active guard shifts and duty pipelines are progressing smoothly on schedule."
          />

          <div className="dg-stats">
            <button type="button" className="dg-stat dg-stat--wide" onClick={() => setEvidence({ title: "All work today", ids: expected })}>
              <span className="dg-stat__label">Done today</span>
              <span className="dg-stat__value dg-num">{done.length}<span className="dg-stat__of">/{expected.length}</span></span>
              <Ramp value={done.length} max={expected.length} />
            </button>
            <StatTile label="Overdue" ids={overdue} tone="danger" onOpen={setEvidence} />
            <StatTile label="Waiting on someone" ids={waiting} tone="neutral" onOpen={setEvidence} />
            <StatTile label="Couldn't be done" ids={blocked} tone="warning" onOpen={setEvidence} />
          </div>

          {data.pipeline.length > 0 && (
            <section className="dg-panel dg-pipe" aria-labelledby="dg-pipe-title">
              <div className="dg-pipe__head">
                <h2 id="dg-pipe-title" className="dg-panel__title">Where each site is</h2>
                <div className="dg-pipe__steps" style={{ gridTemplateColumns: `repeat(${data.steps.length}, minmax(0, 1fr))` }}>
                  {data.steps.map((s, i) => (
                    <div key={s.id} className="dg-pipe__step">
                      <span className="dg-pipe__stepno dg-num">{i + 1}</span>
                      <span>
                        <span className="dg-pipe__stepname">{s.name}</span>
                        <span className="dg-pipe__owner">{s.owner}</span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <ul className="dg-pipe__rows">
                {data.pipeline.map((row) => (
                  <li key={row.site} className="dg-pipe__row">
                    <span className="dg-pipe__site">{row.site}</span>
                    <div className="dg-pipe__track" style={{ gridTemplateColumns: `repeat(${data.steps.length}, minmax(0, 1fr))` }}>
                      {data.steps.map((s, i) => {
                        const cell = row.cells[String(s.id)];
                        const view = cellView(cell);
                        return (
                          <div key={s.id} className={`dg-node dg-node--${view.tone}${i < data.steps.length - 1 ? " has-next" : ""}${view.tone === "done" ? " next-done" : ""}`}>
                            {cell ? (
                              <button type="button" className="dg-node__btn" onClick={() => openTask(cell.task_id)}
                                aria-label={`${row.site}, ${s.name}: ${view.label}. Open task.`}>
                                <span className="dg-node__dot" aria-hidden="true">{view.tone === "done" ? "✓" : view.tone === "overdue" ? "!" : ""}</span>
                                <span className="dg-node__label">{view.label}</span>
                              </button>
                            ) : (
                              <span className="dg-node__btn"><span className="dg-node__dot" aria-hidden="true" /><span className="dg-node__label">—</span></span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section aria-labelledby="dg-people-title" className="dg-daysection">
            <h2 id="dg-people-title" className="dg-section-title">People</h2>
            <div className="dg-people">
              {data.people.map((p) => (
                <article key={p.employee_id} className="dg-person">
                  <header className="dg-person__head">
                    <span className="dg-person__avatar" aria-hidden="true">{initials(p.employee)}</span>
                    <span>
                      <span className="dg-person__name">{p.employee}</span>
                      <span className="dg-person__sub dg-num">{p.done.length} of {p.expected.length} done</span>
                    </span>
                  </header>
                  <Ramp value={p.done.length} max={p.expected.length} />
                  <div className="dg-person__chips">
                    {p.overdue.length > 0 && (
                      <button type="button" className="dg-chip-state dg-chip-state--danger dg-chipbtn" onClick={() => setEvidence({ title: `${p.employee}: overdue`, ids: p.overdue })}>
                        {p.overdue.length} overdue
                      </button>
                    )}
                    {p.waiting.length > 0 && (
                      <button type="button" className="dg-chip-state dg-chipbtn" onClick={() => setEvidence({ title: `${p.employee}: waiting on others`, ids: p.waiting })}>
                        {p.waiting.length} waiting on others
                      </button>
                    )}
                    {p.could_not_complete.length > 0 && (
                      <button type="button" className="dg-chip-state dg-chip-state--warning dg-chipbtn" onClick={() => setEvidence({ title: `${p.employee}: couldn't do`, ids: p.could_not_complete })}>
                        {p.could_not_complete.length} couldn't do
                      </button>
                    )}
                    <button type="button" className="dg-chipbtn dg-person__all" onClick={() => setEvidence({ title: `${p.employee}: today`, ids: p.expected })}>
                      See all
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </>
      )}

      {evidence && (
        <EvidenceModal
          title={evidence.title}
          fields={EVIDENCE_FIELDS}
          load={loadEvidence}
          onOpenRecord={(row) => { setEvidence(null); openTask(row.id); }}
          onClose={() => setEvidence(null)}
        />
      )}
    </div>
  );
}

function StatTile({ label, ids, tone, onOpen }: {
  label: string;
  ids: number[];
  tone: "danger" | "warning" | "neutral";
  onOpen: (e: { title: string; ids: number[] }) => void;
}) {
  return (
    <button type="button" className={`dg-stat${ids.length ? ` dg-stat--${tone}` : ""}`} onClick={() => onOpen({ title: label, ids })} disabled={ids.length === 0}>
      <span className="dg-stat__label">{label}</span>
      <span className="dg-stat__value dg-num">{ids.length}</span>
    </button>
  );
}
