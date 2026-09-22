import { useEffect, useState } from "react";
import {
  fetchEmployeeSnapshot,
  fetchExpectedWorkItems,
  fetchPendingCheckin,
  fetchTeamSnapshots,
  submitCheckinAnswer,
  triggerAdoptionRefresh,
  type AdoptionSnapshot,
  type ExpectedWorkItem,
  type AbandonmentCheckin,
  type CheckinAnswerCode,
  type ExpectedWorkState,
  FACTOR_CONFIG,
  WORKFLOW_LABELS,
  CHECKIN_OPTION_LABELS,
} from "../../api/adoption";
import { resolveEmployeeId } from "../../api/work";
import { useSession } from "../../session/SessionContext";
import { extractErrorMessage } from "../../lib/extractErrorMessage";
import {
  TrendingUpIcon,
  ShieldCheckIcon,
  CheckCircleIcon,
  AlertTriangleIcon,
  SparklesIcon,
} from "../icons";

type ViewTab = "my" | "team";
type ItemFilter = "all" | ExpectedWorkState;

export function AdoptionOverview() {
  const { session } = useSession();
  const [employeeId, setEmployeeId] = useState<number | null>(null);
  const [snapshot, setSnapshot] = useState<AdoptionSnapshot | null>(null);
  const [workItems, setWorkItems] = useState<ExpectedWorkItem[]>([]);
  const [teamSnapshots, setTeamSnapshots] = useState<AdoptionSnapshot[]>([]);
  const [pendingCheckin, setPendingCheckin] = useState<AbandonmentCheckin | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<CheckinAnswerCode | null>(null);
  const [checkinSubmitting, setCheckinSubmitting] = useState(false);
  const [checkinSuccess, setCheckinSuccess] = useState(false);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<ViewTab>("my");
  const [itemFilter, setItemFilter] = useState<ItemFilter>("all");

  const isManagerOrAdmin =
    session?.uid === 2 ||
    session?.login?.toLowerCase().includes("admin") ||
    session?.login?.toLowerCase().includes("manager") ||
    session?.login?.toLowerCase().includes("wilbert") ||
    session?.login?.toLowerCase().includes("kuume") ||
    session?.name?.toLowerCase().includes("admin") ||
    session?.name?.toLowerCase().includes("manager");

  // Resolve employee ID from session
  useEffect(() => {
    if (!session) return;
    resolveEmployeeId(session.uid)
      .then((id) => setEmployeeId(id))
      .catch(() => setEmployeeId(null));
  }, [session]);

  // Load data
  useEffect(() => {
    if (!employeeId) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      fetchEmployeeSnapshot(employeeId),
      fetchExpectedWorkItems(employeeId),
      fetchPendingCheckin(employeeId),
      isManagerOrAdmin ? fetchTeamSnapshots() : Promise.resolve([]),
    ])
      .then(([snap, items, checkin, team]) => {
        if (cancelled) return;
        setSnapshot(snap);
        setWorkItems(items);
        setPendingCheckin(checkin);
        setTeamSnapshots(team);
      })
      .catch((err) => {
        if (!cancelled) setError(extractErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [employeeId, isManagerOrAdmin]);

  async function handleRefresh() {
    setRefreshing(true);
    setError(null);
    try {
      await triggerAdoptionRefresh();
      if (employeeId) {
        const [snap, items, checkin, team] = await Promise.all([
          fetchEmployeeSnapshot(employeeId),
          fetchExpectedWorkItems(employeeId),
          fetchPendingCheckin(employeeId),
          isManagerOrAdmin ? fetchTeamSnapshots() : Promise.resolve([]),
        ]);
        setSnapshot(snap);
        setWorkItems(items);
        setPendingCheckin(checkin);
        setTeamSnapshots(team);
      }
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setRefreshing(false);
    }
  }

  async function handleCheckinSubmit() {
    if (!pendingCheckin || !selectedAnswer) return;
    setCheckinSubmitting(true);
    try {
      await submitCheckinAnswer(pendingCheckin.id, selectedAnswer);
      setCheckinSuccess(true);
      setTimeout(() => {
        setPendingCheckin(null);
        setCheckinSuccess(false);
      }, 2500);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setCheckinSubmitting(false);
    }
  }

  const filteredItems = workItems.filter((item) => {
    if (itemFilter === "all") return true;
    return item.state === itemFilter;
  });

  if (loading) {
    return (
      <div className="dg-adoption__loading">
        <span className="dg-adoption__spinner" aria-hidden="true" />
        <p>Loading adoption metrics and expected work...</p>
      </div>
    );
  }

  return (
    <div className="dg-adoption">
      {/* Header bar */}
      <header className="dg-adoption__header">
        <div className="dg-adoption__header-titles">
          <div className="dg-adoption__header-top">
            <span className="dg-adoption__icon-wrap">
              <TrendingUpIcon size={20} />
            </span>
            <h1 className="dg-adoption__title">Adoption & Operational Execution</h1>
            {snapshot && (
              <span className="dg-adoption__window-badge">
                Window: {snapshot.window_start} → {snapshot.window_end} (7 days)
              </span>
            )}
          </div>
          <p className="dg-adoption__subtitle">
            Measuring operational work executed through DogForce systems — finding where processes need support.
          </p>
        </div>

        <div className="dg-adoption__header-actions">
          {isManagerOrAdmin && (
            <div className="dg-adoption__tab-group" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={tab === "my"}
                className={`dg-adoption__tab-btn${tab === "my" ? " is-active" : ""}`}
                onClick={() => setTab("my")}
              >
                My Adoption
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={tab === "team"}
                className={`dg-adoption__tab-btn${tab === "team" ? " is-active" : ""}`}
                onClick={() => setTab("team")}
              >
                Team Overview
              </button>
            </div>
          )}

          <button
            type="button"
            className="dg-adoption__refresh-btn"
            disabled={refreshing}
            onClick={handleRefresh}
          >
            {refreshing ? "Recomputing..." : "↻ Refresh Metrics"}
          </button>
        </div>
      </header>

      {error && (
        <div className="dg-adoption__alert dg-adoption__alert--error" role="alert">
          <AlertTriangleIcon size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Fairness & Support Policy Banner */}
      <section className="dg-adoption__policy-banner">
        <span className="dg-adoption__policy-icon">
          <ShieldCheckIcon size={18} />
        </span>
        <div className="dg-adoption__policy-content">
          <strong>Fairness & Assistance Guarantee</strong>
          <p>
            Adoption metrics measure whether systems support daily operations. They are strictly{" "}
            <strong>never used for disciplinary actions</strong> (PR-ADO-07). Friction, system errors, and approved leave
            never penalize scores; they trigger assistance.
          </p>
        </div>
      </section>

      {/* Assistance Check-In Prompt (Silent abandonment support) */}
      {pendingCheckin && (
        <section className="dg-adoption__checkin-card" role="region" aria-label="Assistance Check-in">
          <div className="dg-adoption__checkin-head">
            <span className="dg-adoption__checkin-sparkle">
              <SparklesIcon size={18} />
            </span>
            <div>
              <h3 className="dg-adoption__checkin-title">Operational Assistance Check-in</h3>
              <p className="dg-adoption__checkin-desc">
                We noticed an expected operational workflow hasn&apos;t come through recently. What is happening on the ground?
              </p>
            </div>
          </div>

          {checkinSuccess ? (
            <div className="dg-adoption__checkin-success">
              <CheckCircleIcon size={20} />
              <span>Thank you! Your feedback has been recorded. Assistance or config adjustments are underway.</span>
            </div>
          ) : (
            <div className="dg-adoption__checkin-body">
              <div className="dg-adoption__checkin-options">
                {(Object.entries(CHECKIN_OPTION_LABELS) as [CheckinAnswerCode, string][]).map(
                  ([code, label]) => (
                    <label
                      key={code}
                      className={`dg-adoption__checkin-option${selectedAnswer === code ? " is-selected" : ""}`}
                    >
                      <input
                        type="radio"
                        name="checkin_answer"
                        value={code}
                        checked={selectedAnswer === code}
                        onChange={() => setSelectedAnswer(code)}
                      />
                      <span>{label}</span>
                    </label>
                  )
                )}
              </div>

              <div className="dg-adoption__checkin-actions">
                <button
                  type="button"
                  className="dg-adoption__btn dg-adoption__btn--primary"
                  disabled={!selectedAnswer || checkinSubmitting}
                  onClick={handleCheckinSubmit}
                >
                  {checkinSubmitting ? "Submitting..." : "Send Operational Context →"}
                </button>
                <span className="dg-adoption__checkin-note">
                  This routes straight to training or IT support without score deductions.
                </span>
              </div>
            </div>
          )}
        </section>
      )}

      {tab === "my" ? (
        <>
          {/* Main Score Hero Card */}
          <section className="dg-adoption__hero-card">
            <div className="dg-adoption__hero-score-col">
              <span className="dg-adoption__hero-label">Rolling Adoption Score</span>
              {snapshot?.confidence === "insufficient" ? (
                <div className="dg-adoption__score-insufficient">
                  <span className="dg-adoption__score-na">N/A</span>
                  <span className="dg-adoption__score-caption">Not enough activity yet</span>
                </div>
              ) : (
                <div className="dg-adoption__score-display">
                  <span className="dg-adoption__score-value">{snapshot ? snapshot.score : "--"}</span>
                  <span className="dg-adoption__score-max">/ 100</span>
                </div>
              )}

              {/* Confidence Badge */}
              <div className="dg-adoption__confidence-wrap">
                <span
                  className={`dg-adoption__confidence-badge dg-adoption__confidence-badge--${snapshot?.confidence || "insufficient"}`}
                >
                  {snapshot?.confidence === "high" && "High Confidence (≥ 40 items)"}
                  {snapshot?.confidence === "medium" && "Medium Confidence (15–39 items)"}
                  {snapshot?.confidence === "low" && "Low Confidence (5–14 items)"}
                  {(!snapshot || snapshot.confidence === "insufficient") && "Insufficient Sample (< 5 items)"}
                </span>
              </div>
            </div>

            <div className="dg-adoption__hero-stats-col">
              <div className="dg-adoption__stat-box">
                <span className="dg-adoption__stat-label">Expected Work Items</span>
                <span className="dg-adoption__stat-val">{snapshot?.expected_total ?? 0}</span>
                <span className="dg-adoption__stat-sub">Across 5 core workflows</span>
              </div>
              <div className="dg-adoption__stat-box">
                <span className="dg-adoption__stat-label">Fulfilled</span>
                <span className="dg-adoption__stat-val dg-adoption__stat-val--success">
                  {workItems.filter((i) => i.state === "fulfilled").length}
                </span>
                <span className="dg-adoption__stat-sub">
                  {workItems.filter((i) => i.state === "fulfilled" && i.on_time).length} on-time
                </span>
              </div>
              <div className="dg-adoption__stat-box">
                <span className="dg-adoption__stat-label">Legitimately Excused</span>
                <span className="dg-adoption__stat-val dg-adoption__stat-val--info">
                  {snapshot?.excused_total ?? 0}
                </span>
                <span className="dg-adoption__stat-sub">Leave / absence / fault</span>
              </div>
            </div>
          </section>

          {/* 5 Factors Breakdown Grid */}
          <section className="dg-adoption__section">
            <h2 className="dg-adoption__section-title">Score Breakdown by Operational Factor</h2>
            <p className="dg-adoption__section-desc">
              Every point represents genuine system operations. Factors are weighted by operational importance.
            </p>

            <div className="dg-adoption__factors-grid">
              {(snapshot?.factors && snapshot.factors.length > 0
                ? snapshot.factors
                : Object.entries(FACTOR_CONFIG).map(([k, cfg]) => ({
                    id: 0,
                    factor_key: k as keyof typeof FACTOR_CONFIG,
                    weight: cfg.weight,
                    raw_value: 0,
                    weighted_value: 0,
                  }))
              ).map((factor) => {
                const cfg = FACTOR_CONFIG[factor.factor_key] || {
                  label: factor.factor_key,
                  weight: factor.weight,
                  description: "",
                };
                const rawPercent = Math.round(factor.raw_value);
                const maxPoints = Math.round(cfg.weight * 100);
                const earnedPoints = (factor.weighted_value || (factor.raw_value * cfg.weight)).toFixed(1);

                return (
                  <div key={factor.factor_key} className="dg-adoption__factor-card">
                    <div className="dg-adoption__factor-head">
                      <h4 className="dg-adoption__factor-name">{cfg.label}</h4>
                      <span className="dg-adoption__factor-weight">Weight: {Math.round(cfg.weight * 100)}%</span>
                    </div>

                    <p className="dg-adoption__factor-desc">{cfg.description}</p>

                    <div className="dg-adoption__factor-bar-wrap">
                      <div className="dg-adoption__factor-bar">
                        <div
                          className="dg-adoption__factor-bar-fill"
                          style={{ width: `${Math.min(100, Math.max(0, rawPercent))}%` }}
                        />
                      </div>
                      <div className="dg-adoption__factor-bar-labels">
                        <span>{rawPercent}% raw</span>
                        <strong>{earnedPoints} / {maxPoints} pts</strong>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Expected Work Items Explorer (Score Explanation) */}
          <section className="dg-adoption__section">
            <div className="dg-adoption__section-header">
              <div>
                <h2 className="dg-adoption__section-title">Score Explanation: Expected Work Items</h2>
                <p className="dg-adoption__section-desc">
                  Every score explains itself down to individual events. No secret algorithms or black boxes.
                </p>
              </div>

              {/* Filter chips */}
              <div className="dg-adoption__filter-chips" role="group" aria-label="Item state filters">
                {(["all", "fulfilled", "missed", "excused"] as ItemFilter[]).map((f) => (
                  <button
                    key={f}
                    type="button"
                    className={`dg-adoption__chip${itemFilter === f ? " is-active" : ""}`}
                    onClick={() => setItemFilter(f)}
                  >
                    {f === "all" && `All (${workItems.length})`}
                    {f === "fulfilled" && `Fulfilled (${workItems.filter((i) => i.state === "fulfilled").length})`}
                    {f === "missed" && `Missed (${workItems.filter((i) => i.state === "missed").length})`}
                    {f === "excused" && `Excused (${workItems.filter((i) => i.state === "excused").length})`}
                  </button>
                ))}
              </div>
            </div>

            {filteredItems.length === 0 ? (
              <div className="dg-adoption__empty-box">
                <p>No expected work items found matching this filter in the current window.</p>
              </div>
            ) : (
              <div className="dg-adoption__table-wrap">
                <table className="dg-adoption__table">
                  <thead>
                    <tr>
                      <th>Workflow</th>
                      <th>Period Date</th>
                      <th>Due Target</th>
                      <th>Execution</th>
                      <th>Status & Explanation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredItems.map((item) => {
                      const wfName = WORKFLOW_LABELS[item.workflow_key] || item.workflow_key;
                      return (
                        <tr key={item.id}>
                          <td>
                            <strong className="dg-adoption__item-title">{wfName}</strong>
                            {item.site_id && (
                              <span className="dg-adoption__item-sub">{item.site_id[1]}</span>
                            )}
                          </td>
                          <td className="dg-adoption__mono-cell">{item.period_date}</td>
                          <td className="dg-adoption__mono-cell">
                            {item.due_at ? item.due_at.split(" ")[1]?.slice(0, 5) || item.due_at : "By end of day"}
                          </td>
                          <td className="dg-adoption__mono-cell">
                            {item.fulfilled_at
                              ? item.fulfilled_at.split(" ")[1]?.slice(0, 5) || item.fulfilled_at
                              : "--"}
                          </td>
                          <td>
                            {item.state === "fulfilled" && (
                              <span
                                className={`dg-badge dg-badge--${item.on_time ? "success" : "warning"}`}
                              >
                                {item.on_time ? "✓ On Time" : "⚠ Late Fulfilled"}
                              </span>
                            )}
                            {item.state === "missed" && (
                              <span className="dg-badge dg-badge--danger">
                                ✗ Missed
                              </span>
                            )}
                            {item.state === "excused" && (
                              <span className="dg-badge dg-badge--info">
                                Excused: {item.excusal_reason ? item.excusal_reason.replace("_", " ") : "Policy"}
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : (
        /* Team Overview Tab */
        <section className="dg-adoption__section">
          <h2 className="dg-adoption__section-title">Team Operational Adoption</h2>
          <p className="dg-adoption__section-desc">
            Rolling 7-day snapshots across staff. Used to spot where workflows are blocking teams.
          </p>

          <div className="dg-adoption__table-wrap">
            <table className="dg-adoption__table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Window</th>
                  <th>Expected Items</th>
                  <th>Excused</th>
                  <th>Confidence</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {teamSnapshots.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", padding: 24, color: "var(--ds-text-subtle)" }}>
                      No team adoption snapshots computed yet. Click &quot;Refresh Metrics&quot; above.
                    </td>
                  </tr>
                ) : (
                  teamSnapshots.map((snap) => {
                    const empName = Array.isArray(snap.employee_id)
                      ? snap.employee_id[1]
                      : `Employee #${snap.employee_id}`;

                    return (
                      <tr key={snap.id}>
                        <td><strong>{empName}</strong></td>
                        <td className="dg-adoption__mono-cell">{snap.window_start} → {snap.window_end}</td>
                        <td className="dg-adoption__mono-cell">{snap.expected_total}</td>
                        <td className="dg-adoption__mono-cell">{snap.excused_total}</td>
                        <td>
                          <span className={`dg-badge dg-badge--${snap.confidence === "high" || snap.confidence === "medium" ? "success" : "warning"}`}>
                            {snap.confidence}
                          </span>
                        </td>
                        <td>
                          {snap.confidence === "insufficient" ? (
                            <span style={{ color: "var(--ds-text-subtle)" }}>N/A (low items)</span>
                          ) : (
                            <strong className="dg-adoption__score-pill">{snap.score} / 100</strong>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
