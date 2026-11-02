import { useCallback, useState } from "react";
import { fetchDrillDownRecords, fetchOwnerOverview, type OwnerMetricTile, type OwnerOverviewData } from "../../api/support";
import { EvidenceModal } from "../../components/EvidenceModal";
import { ErrorState } from "../../components/States";
import { OwnerOverviewSkeleton } from "../../components/Skeletons";
import { Ramp } from "../../components/Ramp";
import { AttentionCard, type AttentionItem } from "../../components/AttentionCard";
import { useQuery } from "../../lib/queryCache";
import { TrendingUpIcon } from "../icons";

const TREND_WORDS = { up: "Improving", down: "Slipping", flat: "Steady" } as const;

/**
 * The owner's and GM's company-wide picture. Every tile is a count of real
 * records; opening it shows exactly those records. The trend states the
 * counts it compares.
 */
export function OwnerOverview({ reloadSignal }: { reloadSignal?: number }) {
  const [drill, setDrill] = useState<OwnerMetricTile | null>(null);

  const {
    data,
    error,
    isLoading,
    refetch,
  } = useQuery<OwnerOverviewData>(
    "owner:overview",
    fetchOwnerOverview,
    { reloadSignal, staleTime: 30_000 },
  );

  const loadDrill = useCallback(
    () => (drill ? fetchDrillDownRecords<Record<string, unknown> & { id: number }>(drill.drill) : Promise.resolve([])),
    [drill],
  );

  if (error) return <ErrorState error={error} fallback="The overview couldn't be loaded." onRetry={() => void refetch()} />;
  if (isLoading && !data) return <OwnerOverviewSkeleton />;
  if (!data) return <OwnerOverviewSkeleton />;

  const [feature, ...rest] = data.tiles;
  const needsAttention = rest.filter((t) => t.tone === "danger" || t.tone === "warning").length;
  const dateLine = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });

  const attentionItems: AttentionItem[] = rest
    .filter((t) => t.tone === "danger" || t.tone === "warning")
    .map((t) => ({
      id: t.key,
      tone: (t.tone === "danger" ? "danger" : "warning") as "danger" | "warning",
      title: `${t.label}: ${t.value}${t.total != null ? ` / ${t.total}` : ""}`,
      detail: t.detail,
      actionLabel: "Inspect records",
      onAction: () => setDrill(t),
    }));

  return (
    <div className="dg-owner dg-page-enter">
      <header className="dg-hero">
        <div className="dg-hero__text">
          <p className="dg-eyebrow">{dateLine}</p>
          <h1 className="dg-display">How DogForce is doing</h1>
          <p className="dg-subline">
            {needsAttention === 0 ? "Nothing needs your attention right now." : `${needsAttention} ${needsAttention === 1 ? "area needs" : "areas need"} attention.`}{" "}
            Counted from the records just now. Open any number to see what's behind it.
          </p>
        </div>
      </header>

      <AttentionCard
        title="Executive Digest"
        subtitle="Automated executive triage of compliance risks, billing milestones, and operational variances"
        badge="Owner Digest"
        items={attentionItems}
        emptyMessage="Company-wide operations, client renewals, and compliance benchmarks are fully healthy."
      />

      {feature && (
        <button type="button" className="dg-feature" onClick={() => setDrill(feature)}>
          <span className="dg-feature__main">
            <span className="dg-feature__label">{feature.label}</span>
            <span className="dg-feature__value dg-num">
              {feature.value}{feature.total != null && <span className="dg-feature__of">/{feature.total}</span>}
            </span>
            <span className="dg-feature__detail">{feature.detail}</span>
            {feature.total != null && <Ramp value={feature.value} max={feature.total} />}
          </span>
          {feature.trend && (
            <span className={`dg-feature__trend is-${feature.trend.direction}`}>
              <span className="dg-feature__trendhead">
                <TrendingUpIcon size={18} /> {TREND_WORDS[feature.trend.direction]}
                <b className="dg-num">{feature.trend.current_pct}%</b>
              </span>
              <span className="dg-feature__trendtext">{feature.trend.explanation}</span>
            </span>
          )}
        </button>
      )}

      <div className="dg-tiles">
        {rest.map((tile) => (
          <button key={tile.key} type="button" className={`dg-tile2 dg-tile2--${tile.tone}`} onClick={() => setDrill(tile)}>
            <span className="dg-tile2__top">
              <span className="dg-tile2__dot" aria-hidden="true" />
              <span className="dg-tile2__label">{tile.label}</span>
            </span>
            <span className="dg-tile2__value dg-num">{tile.value}</span>
            <span className="dg-tile2__detail">{tile.detail}</span>
            <span className="dg-tile2__go">See the records →</span>
          </button>
        ))}
      </div>

      {drill && (
        <EvidenceModal title={drill.drill.title} fields={drill.drill.fields} load={loadDrill} onClose={() => setDrill(null)} />
      )}
    </div>
  );
}
