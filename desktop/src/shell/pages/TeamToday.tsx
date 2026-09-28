import { useCallback, useEffect, useState } from "react";
import { fetchTasksByIds, fetchTeamToday, type TeamCell, type TeamToday as TeamTodayData } from "../../api/today";
import { EvidenceModal } from "../../components/EvidenceModal";
import { EmptyState, ErrorState } from "../../components/States";
import { useViewMode } from "../../app/viewMode";

const TASK_PATH = "/odoo/action-security_work.action_security_work_task";
const EVIDENCE_FIELDS = ["name", "employee_id", "site_id", "due_at", "state", "cnc_reason", "cnc_note"];

function cellView(cell: TeamCell | undefined): { label: string; tone: string } {
  if (!cell) return { label: "Not expected", tone: "none" };
  if (cell.state === "verified") return { label: "Done ✓", tone: "success" };
  if (cell.state === "submitted") return { label: "Done", tone: "success" };
  if (cell.state === "could_not_complete") return { label: "Couldn't do", tone: "warning" };
  if (cell.is_overdue) return { label: "Overdue", tone: "danger" };
  if (cell.readiness === "waiting") return { label: "Waiting", tone: "neutral" };
  if (cell.state === "in_progress") return { label: "In progress", tone: "info" };
  return { label: "To do", tone: "info" };
}

/**
 * The GM's "where is it stuck?" view. One row per rostered site, one column
 * per step of the pipeline, and each cell is the real task. Below that, per
 * person: expected, done, overdue, couldn't do. Every number opens the
 * records behind it. Nothing is a score.
 */
export function TeamToday({ reloadSignal }: { reloadSignal?: number }) {
  const { openInOdoo } = useViewMode();
  const [data, setData] = useState<TeamTodayData | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [evidence, setEvidence] = useState<{ title: string; ids: number[] } | null>(null);

  const load = useCallback(() => {
    setError(null);
    fetchTeamToday().then(setData).catch(setError);
  }, []);
  useEffect(() => { load(); }, [load, reloadSignal]);

  const loadEvidence = useCallback(() => fetchTasksByIds(evidence?.ids ?? []), [evidence]);

  if (error) return <ErrorState error={error} fallback="Team Today couldn't be loaded." onRetry={load} />;
  if (!data) return <div className="dg-skeleton dg-skeleton--card" />;

  const openTask = (id: number) => void openInOdoo(`${TASK_PATH}/${id}`);

  return (
    <div className="dg-page-enter dg-team">
      <header className="dg-page-head">
        <h1 className="dg-page-title">Team today</h1>
        <p className="dg-field__hint">{new Date(`${data.date}T12:00:00`).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })}. Every cell and number opens the records behind it.</p>
      </header>

      {data.pipeline.length === 0 && data.people.length === 0 && (
        <EmptyState title="No work is expected today">
          Tasks appear here once the roster has guards at sites and duties have owners (Work → Set up attendance pipeline).
        </EmptyState>
      )}

      {data.pipeline.length > 0 && (
        <section aria-labelledby="dg-pipeline-title">
          <h2 id="dg-pipeline-title" className="dg-section-title">Where each site is</h2>
          <div className="dg-table-wrap">
            <table className="dg-table dg-pipeline">
              <thead>
                <tr>
                  <th scope="col">Site</th>
                  {data.steps.map((s) => (
                    <th key={s.id} scope="col">{s.name}<div className="dg-field__hint">{s.owner}</div></th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.pipeline.map((row) => (
                  <tr key={row.site}>
                    <th scope="row">{row.site}</th>
                    {data.steps.map((s) => {
                      const cell = row.cells[String(s.id)];
                      const view = cellView(cell);
                      return (
                        <td key={s.id}>
                          {cell ? (
                            <button type="button" className={`dg-cell dg-cell--${view.tone}`} onClick={() => openTask(cell.task_id)}
                              aria-label={`${row.site}, ${s.name}: ${view.label}. Open task.`}>
                              {view.label}
                            </button>
                          ) : <span className="dg-cell dg-cell--none">—</span>}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {data.people.length > 0 && (
        <section aria-labelledby="dg-people-title">
          <h2 id="dg-people-title" className="dg-section-title">By person</h2>
          <div className="dg-table-wrap">
            <table className="dg-table">
              <thead>
                <tr>
                  <th scope="col">Who</th>
                  <th scope="col">Expected</th>
                  <th scope="col">Done</th>
                  <th scope="col">Overdue</th>
                  <th scope="col">Couldn't do</th>
                  <th scope="col">Waiting on others</th>
                </tr>
              </thead>
              <tbody>
                {data.people.map((p) => (
                  <tr key={p.employee_id}>
                    <th scope="row">{p.employee}</th>
                    {(["expected", "done", "overdue", "could_not_complete", "waiting"] as const).map((k) => (
                      <td key={k}>
                        {p[k].length > 0 ? (
                          <button type="button" className={`dg-countbtn${k === "overdue" ? " is-danger" : ""}`}
                            onClick={() => setEvidence({ title: `${p.employee}: ${k.replace(/_/g, " ")}`, ids: p[k] })}>
                            {p[k].length}
                          </button>
                        ) : "0"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
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
