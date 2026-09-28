import { useCallback, useEffect, useState } from "react";
import { fetchDrillDownRecords, fetchOwnerOverview, type OwnerMetricTile, type OwnerOverviewData } from "../../api/support";
import { EvidenceModal } from "../../components/EvidenceModal";
import { ErrorState } from "../../components/States";

const TREND_WORDS = { up: "Improving", down: "Getting worse", flat: "Steady" } as const;

/**
 * The owner's and GM's company-wide picture. Every tile is a count of real
 * records, and opening it shows exactly those records. The trend line states
 * the counts it compares. Nothing here is modelled or AI-generated.
 */
export function OwnerOverview({ reloadSignal }: { reloadSignal?: number }) {
  const [data, setData] = useState<OwnerOverviewData | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [drill, setDrill] = useState<OwnerMetricTile | null>(null);

  const load = useCallback(() => {
    setError(null);
    fetchOwnerOverview().then(setData).catch(setError);
  }, []);
  useEffect(() => { load(); }, [load, reloadSignal]);

  const loadDrill = useCallback(
    () => (drill ? fetchDrillDownRecords<Record<string, unknown> & { id: number }>(drill.drill) : Promise.resolve([])),
    [drill],
  );

  if (error) return <ErrorState error={error} fallback="The overview couldn't be loaded." onRetry={load} />;
  if (!data) return <div className="dg-skeleton dg-skeleton--card" />;

  return (
    <div className="dg-page-enter">
      <header className="dg-page-head">
        <h1 className="dg-page-title">How DogForce is doing today</h1>
        <p className="dg-field__hint">Counted from the records just now. Open any tile to see exactly what's behind it.</p>
      </header>

      <div className="dg-metrics">
        {data.tiles.map((tile) => (
          <button key={tile.key} type="button" className={`dg-metric dg-metric--${tile.tone}`} onClick={() => setDrill(tile)}>
            <span className="dg-metric__label">{tile.label}</span>
            <span className="dg-metric__value">
              {tile.value}
              {tile.total != null && <span className="dg-metric__total"> / {tile.total}</span>}
            </span>
            <span className="dg-metric__detail">{tile.detail}</span>
            {tile.trend && (
              <span className="dg-metric__trend" title={tile.trend.explanation}>
                {TREND_WORDS[tile.trend.direction]}: {tile.trend.explanation}
              </span>
            )}
          </button>
        ))}
      </div>

      {drill && (
        <EvidenceModal
          title={drill.drill.title}
          fields={drill.drill.fields}
          load={loadDrill}
          onClose={() => setDrill(null)}
        />
      )}
    </div>
  );
}
