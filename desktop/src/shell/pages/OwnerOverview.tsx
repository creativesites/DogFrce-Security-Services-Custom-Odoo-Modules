import { useEffect, useState } from "react";
import {
  fetchOwnerOverview,
  fetchDrillDownRecords,
  type OwnerOverviewData,
  type OwnerMetricTile,
} from "../../api/support";

interface DrillDownState {
  title: string;
  tile: OwnerMetricTile;
  loading: boolean;
  records: Array<Record<string, unknown>>;
  error: string | null;
}

export function OwnerOverview() {
  const [data, setData] = useState<OwnerOverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drillDown, setDrillDown] = useState<DrillDownState | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchOwnerOverview()
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleOpenDrillDown(title: string, tile: OwnerMetricTile) {
    setDrillDown({
      title,
      tile,
      loading: true,
      records: [],
      error: null,
    });

    try {
      const recs = await fetchDrillDownRecords(
        tile.drill_down_model,
        tile.drill_down_domain,
        ["id", "name", "display_name", "state", "create_date", "due_at"],
        50,
      );
      setDrillDown((prev) => (prev ? { ...prev, loading: false, records: recs } : null));
    } catch (err) {
      setDrillDown((prev) =>
        prev
          ? {
              ...prev,
              loading: false,
              error: err instanceof Error ? err.message : String(err),
            }
          : null,
      );
    }
  }

  if (loading) {
    return (
      <div className="dg-appview__body" style={{ padding: 24, textAlign: "center", color: "var(--ds-text-subtle)" }}>
        Loading operational metrics...
      </div>
    );
  }

  if (error) {
    return (
      <div className="dg-appview__body" style={{ padding: 24 }}>
        <div style={{ background: "var(--ds-danger-bg)", color: "var(--ds-danger)", padding: 16, borderRadius: 8 }}>
          Failed to load owner overview: {error}
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="dg-appview__body" style={{ padding: "20px 24px", overflowY: "auto" }}>
      <div style={{ marginBottom: 20, display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <h1 style={{ margin: "0 0 4px 0", fontSize: "1.35rem", fontWeight: 700 }}>Owner &amp; Executive Overview</h1>
          <div style={{ fontSize: "0.85rem", color: "var(--ds-text-muted)" }}>
            Rolling Window: {data.period_start} to {data.period_end} · Deterministic Digest
          </div>
        </div>
      </div>

      {/* 6 Metric Tiles Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16, marginBottom: 24 }}>
        {/* 1. Workflow Coverage */}
        <div
          onClick={() => handleOpenDrillDown("Workflow Coverage Items", data.workflow_coverage)}
          style={{
            background: "var(--ds-surface)",
            borderRadius: 10,
            padding: 16,
            border: "1px solid var(--ds-border)",
            cursor: "pointer",
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
          }}
        >
          <div style={{ fontSize: "0.82rem", color: "var(--ds-text-subtle)", fontWeight: 600, textTransform: "uppercase", marginBottom: 8 }}>
            Workflow Coverage
          </div>
          <div style={{ fontSize: "2rem", fontWeight: 700, fontFamily: "var(--dgs-mono, monospace)", color: "var(--ds-accent)" }}>
            {data.workflow_coverage.value}%
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--ds-text-subtle)", marginTop: 4 }}>
            {data.workflow_coverage.numerator} fulfilled / {data.workflow_coverage.denominator} net expected
          </div>
          <div style={{ marginTop: 8, fontSize: "0.78rem", color: "var(--ds-accent)", fontWeight: 500 }}>
            View drill-down →
          </div>
        </div>

        {/* 2. On-Time Rate */}
        <div
          onClick={() => handleOpenDrillDown("On-Time Fulfilled Items", data.on_time_rate)}
          style={{
            background: "var(--ds-surface)",
            borderRadius: 10,
            padding: 16,
            border: "1px solid var(--ds-border)",
            cursor: "pointer",
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
          }}
        >
          <div style={{ fontSize: "0.82rem", color: "var(--ds-text-subtle)", fontWeight: 600, textTransform: "uppercase", marginBottom: 8 }}>
            On-Time Rate
          </div>
          <div style={{ fontSize: "2rem", fontWeight: 700, fontFamily: "var(--dgs-mono, monospace)", color: "var(--ds-success)" }}>
            {data.on_time_rate.value}%
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--ds-text-subtle)", marginTop: 4 }}>
            {data.on_time_rate.numerator} on-time / {data.on_time_rate.denominator} completed
          </div>
          <div style={{ marginTop: 8, fontSize: "0.78rem", color: "var(--ds-accent)", fontWeight: 500 }}>
            View drill-down →
          </div>
        </div>

        {/* 3. Overdue Open Tasks */}
        <div
          onClick={() => handleOpenDrillDown("Overdue Open Work Tasks", data.overdue_open)}
          style={{
            background: "var(--ds-surface)",
            borderRadius: 10,
            padding: 16,
            border: "1px solid var(--ds-border)",
            cursor: "pointer",
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
          }}
        >
          <div style={{ fontSize: "0.82rem", color: "var(--ds-text-subtle)", fontWeight: 600, textTransform: "uppercase", marginBottom: 8 }}>
            Overdue Open Tasks
          </div>
          <div style={{ fontSize: "2rem", fontWeight: 700, fontFamily: "var(--dgs-mono, monospace)", color: data.overdue_open.value > 0 ? "var(--ds-danger)" : "var(--ds-success)" }}>
            {data.overdue_open.value}
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--ds-text-subtle)", marginTop: 4 }}>
            Tasks past due date awaiting submission
          </div>
          <div style={{ marginTop: 8, fontSize: "0.78rem", color: "var(--ds-accent)", fontWeight: 500 }}>
            View drill-down →
          </div>
        </div>

        {/* 4. Support Load */}
        <div
          onClick={() => handleOpenDrillDown("Open Support Requests", data.support_load)}
          style={{
            background: "var(--ds-surface)",
            borderRadius: 10,
            padding: 16,
            border: "1px solid var(--ds-border)",
            cursor: "pointer",
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
          }}
        >
          <div style={{ fontSize: "0.82rem", color: "var(--ds-text-subtle)", fontWeight: 600, textTransform: "uppercase", marginBottom: 8 }}>
            Support Load
          </div>
          <div style={{ fontSize: "2rem", fontWeight: 700, fontFamily: "var(--dgs-mono, monospace)", color: data.support_load.value > 0 ? "var(--ds-warning)" : "var(--ds-success)" }}>
            {data.support_load.value}
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--ds-text-subtle)", marginTop: 4 }}>
            Open support &amp; problem tickets
          </div>
          <div style={{ marginTop: 8, fontSize: "0.78rem", color: "var(--ds-accent)", fontWeight: 500 }}>
            View drill-down →
          </div>
        </div>

        {/* 5. Friction Rate */}
        <div
          onClick={() => handleOpenDrillDown("Friction & Difficult Tasks", data.friction_rate)}
          style={{
            background: "var(--ds-surface)",
            borderRadius: 10,
            padding: 16,
            border: "1px solid var(--ds-border)",
            cursor: "pointer",
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
          }}
        >
          <div style={{ fontSize: "0.82rem", color: "var(--ds-text-subtle)", fontWeight: 600, textTransform: "uppercase", marginBottom: 8 }}>
            Friction Rate
          </div>
          <div style={{ fontSize: "2rem", fontWeight: 700, fontFamily: "var(--dgs-mono, monospace)", color: "var(--ds-info)" }}>
            {data.friction_rate.value}
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--ds-text-subtle)", marginTop: 4 }}>
            Signals per 100 expected items
          </div>
          <div style={{ marginTop: 8, fontSize: "0.78rem", color: "var(--ds-accent)", fontWeight: 500 }}>
            View drill-down →
          </div>
        </div>

        {/* 6. Coverage Gap */}
        <div
          onClick={() => handleOpenDrillDown("Unfilled Roster Slots (Next 24h)", data.coverage_gap)}
          style={{
            background: "var(--ds-surface)",
            borderRadius: 10,
            padding: 16,
            border: "1px solid var(--ds-border)",
            cursor: "pointer",
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
          }}
        >
          <div style={{ fontSize: "0.82rem", color: "var(--ds-text-subtle)", fontWeight: 600, textTransform: "uppercase", marginBottom: 8 }}>
            Coverage Gap (24h)
          </div>
          <div style={{ fontSize: "2rem", fontWeight: 700, fontFamily: "var(--dgs-mono, monospace)", color: data.coverage_gap.value > 0 ? "var(--ds-danger)" : "var(--ds-success)" }}>
            {data.coverage_gap.value}
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--ds-text-subtle)", marginTop: 4 }}>
            Unfilled slots in next 24 hours
          </div>
          <div style={{ marginTop: 8, fontSize: "0.78rem", color: "var(--ds-accent)", fontWeight: 500 }}>
            View drill-down →
          </div>
        </div>
      </div>

      {/* Drill-down Modal */}
      {drillDown && (
        <div className="dg-modal-backdrop" role="dialog" aria-modal="true" aria-label="Drill Down">
          <div className="dg-modal" style={{ maxWidth: 650, maxHeight: "80vh", display: "flex", flexDirection: "column" }}>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--ds-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h3 style={{ margin: 0, fontSize: "1.1rem" }}>{drillDown.title}</h3>
                <div style={{ fontSize: "0.8rem", color: "var(--ds-text-subtle)" }}>
                  Model: <code>{drillDown.tile.drill_down_model}</code> ({drillDown.tile.value} matching)
                </div>
              </div>
              <button
                type="button"
                className="dg-btn dg-btn--secondary"
                style={{ padding: "4px 8px" }}
                onClick={() => setDrillDown(null)}
              >
                ✕
              </button>
            </div>

            <div style={{ padding: "16px 20px", overflowY: "auto", flex: 1 }}>
              {drillDown.loading && <div style={{ textAlign: "center", padding: 20 }}>Loading records...</div>}
              {drillDown.error && (
                <div style={{ background: "var(--ds-danger-bg)", color: "var(--ds-danger)", padding: 10, borderRadius: 6 }}>
                  {drillDown.error}
                </div>
              )}
              {!drillDown.loading && drillDown.records.length === 0 && (
                <div style={{ textAlign: "center", color: "var(--ds-text-subtle)", padding: 20 }}>
                  No individual records found matching this filter.
                </div>
              )}
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {drillDown.records.map((r) => (
                  <div
                    key={String(r.id)}
                    style={{
                      padding: "10px 12px",
                      borderRadius: 6,
                      background: "var(--ds-surface)",
                      border: "1px solid var(--ds-border)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      fontSize: "0.88rem",
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600 }}>{String(r.display_name || r.name || `Record #${r.id}`)}</div>
                      {Boolean(r.due_at) && <div style={{ fontSize: "0.78rem", color: "var(--ds-text-subtle)" }}>Due: {String(r.due_at)}</div>}
                    </div>
                    {Boolean(r.state) && (
                      <span className="dg-chip" style={{ fontSize: "0.75rem" }}>
                        {String(r.state)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div style={{ padding: "12px 20px", borderTop: "1px solid var(--ds-border)", display: "flex", justifyContent: "flex-end" }}>
              <button
                type="button"
                className="dg-btn dg-btn--secondary"
                onClick={() => setDrillDown(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
