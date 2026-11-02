import type { CSSProperties } from "react";

interface SkeletonProps {
  width?: number | string;
  height?: number | string;
  borderRadius?: number | string;
  className?: string;
  style?: CSSProperties;
}

/** Basic atomic skeleton block with shimmer animation. */
export function Skeleton({ width, height, borderRadius, className = "", style }: SkeletonProps) {
  const inlineStyle: CSSProperties = {
    ...style,
    ...(width != null ? { width } : {}),
    ...(height != null ? { height } : {}),
    ...(borderRadius != null ? { borderRadius } : {}),
  };
  return <div className={`dg-skeleton ${className}`} style={inlineStyle} aria-hidden="true" />;
}

/** Living skeleton matching Home ("Today") layout geometry with zero layout shift. */
export function HomeSkeleton() {
  return (
    <div className="dg-today dg-page-enter" role="status" aria-label="Loading today's work">
      <header className="dg-hero">
        <div className="dg-hero__text">
          <Skeleton width={130} height={12} className="dg-skeleton-text--eyebrow" />
          <Skeleton width={280} height={32} className="dg-skeleton-text--title" />
          <Skeleton width={320} height={16} className="dg-skeleton-text--subline" />
        </div>
        <Skeleton width={72} height={72} className="dg-skeleton-circle" />
      </header>

      <div className="dg-today__grid">
        <div className="dg-today__main">
          {/* Up Next Card Skeleton */}
          <div className="dg-upnext dg-skeleton-card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <Skeleton width={90} height={20} className="dg-skeleton-pill" />
              <Skeleton width={80} height={14} className="dg-skeleton-text" />
            </div>
            <div>
              <Skeleton width="65%" height={24} style={{ marginBottom: 8 }} />
              <Skeleton width={110} height={16} className="dg-skeleton-pill" />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <Skeleton width="92%" height={14} className="dg-skeleton-text" />
              <Skeleton width="75%" height={14} className="dg-skeleton-text" />
            </div>
            <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
              <Skeleton width={120} height={36} className="dg-skeleton-btn" />
              <Skeleton width={100} height={36} className="dg-skeleton-btn" />
            </div>
          </div>

          {/* Timeline Section Skeleton */}
          <section className="dg-daysection" style={{ marginTop: 24 }}>
            <Skeleton width={100} height={18} style={{ marginBottom: 14 }} />
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div className="dg-skeleton-row">
                <Skeleton width={44} height={14} className="dg-skeleton-text" />
                <Skeleton width="40%" height={16} />
                <div style={{ marginLeft: "auto" }}>
                  <Skeleton width={80} height={22} className="dg-skeleton-pill" />
                </div>
              </div>
              <div className="dg-skeleton-row">
                <Skeleton width={44} height={14} className="dg-skeleton-text" />
                <Skeleton width="48%" height={16} />
                <div style={{ marginLeft: "auto" }}>
                  <Skeleton width={80} height={22} className="dg-skeleton-pill" />
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Aside Panel Skeleton */}
        <aside className="dg-today__aside" aria-hidden="true">
          <div className="dg-panel dg-skeleton-card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <Skeleton width={100} height={16} style={{ marginBottom: 4 }} />
            <Skeleton width="100%" height={32} />
            <Skeleton width="100%" height={32} />
          </div>
        </aside>
      </div>
    </div>
  );
}

/** Living skeleton matching Team Today layout. */
export function TeamTodaySkeleton() {
  return (
    <div className="dg-team dg-page-enter" role="status" aria-label="Loading team operations">
      <header className="dg-hero">
        <div className="dg-hero__text">
          <Skeleton width={140} height={12} className="dg-skeleton-text--eyebrow" />
          <Skeleton width={220} height={32} className="dg-skeleton-text--title" />
          <Skeleton width={420} height={16} className="dg-skeleton-text--subline" />
        </div>
      </header>

      {/* 4 Stat Cards */}
      <div className="dg-stats" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
        <div className="dg-stat dg-stat--wide dg-skeleton-card" style={{ padding: 18 }}>
          <Skeleton width={90} height={12} style={{ marginBottom: 10 }} />
          <Skeleton width={60} height={28} style={{ marginBottom: 12 }} />
          <Skeleton width="100%" height={8} className="dg-skeleton-pill" />
        </div>
        <div className="dg-stat dg-skeleton-card" style={{ padding: 18 }}>
          <Skeleton width={70} height={12} style={{ marginBottom: 10 }} />
          <Skeleton width={50} height={28} />
        </div>
        <div className="dg-stat dg-skeleton-card" style={{ padding: 18 }}>
          <Skeleton width={110} height={12} style={{ marginBottom: 10 }} />
          <Skeleton width={50} height={28} />
        </div>
        <div className="dg-stat dg-skeleton-card" style={{ padding: 18 }}>
          <Skeleton width={90} height={12} style={{ marginBottom: 10 }} />
          <Skeleton width={50} height={28} />
        </div>
      </div>

      {/* Pipeline Matrix Skeleton */}
      <section className="dg-panel dg-pipe dg-skeleton-card" style={{ marginTop: 20, padding: 20 }}>
        <Skeleton width={160} height={20} style={{ marginBottom: 16 }} />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 16 }}>
          <Skeleton height={36} className="dg-skeleton-tile" />
          <Skeleton height={36} className="dg-skeleton-tile" />
          <Skeleton height={36} className="dg-skeleton-tile" />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <Skeleton height={50} className="dg-skeleton-tile" />
          <Skeleton height={50} className="dg-skeleton-tile" />
          <Skeleton height={50} className="dg-skeleton-tile" />
        </div>
      </section>
    </div>
  );
}

/** Living skeleton matching Owner Overview layout. */
export function OwnerOverviewSkeleton() {
  return (
    <div className="dg-owner dg-page-enter" role="status" aria-label="Loading company overview">
      <header className="dg-hero">
        <div className="dg-hero__text">
          <Skeleton width={140} height={12} className="dg-skeleton-text--eyebrow" />
          <Skeleton width={260} height={32} className="dg-skeleton-text--title" />
          <Skeleton width={420} height={16} className="dg-skeleton-text--subline" />
        </div>
      </header>

      {/* Feature Banner Skeleton */}
      <div className="dg-feature dg-skeleton-card" style={{ padding: 24, marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div style={{ width: "60%" }}>
            <Skeleton width={160} height={14} style={{ marginBottom: 10 }} />
            <Skeleton width={120} height={42} style={{ marginBottom: 12 }} />
            <Skeleton width="90%" height={14} style={{ marginBottom: 14 }} />
            <Skeleton width="100%" height={10} className="dg-skeleton-pill" />
          </div>
          <div style={{ width: 140 }}>
            <Skeleton width={120} height={40} className="dg-skeleton-tile" />
          </div>
        </div>
      </div>

      {/* 4 Metric Tiles */}
      <div className="dg-tiles" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
        <div className="dg-tile2 dg-skeleton-tile" style={{ height: 130 }}>
          <Skeleton width={120} height={14} style={{ marginBottom: 12 }} />
          <Skeleton width={50} height={32} style={{ marginBottom: 10 }} />
          <Skeleton width="80%" height={12} />
        </div>
        <div className="dg-tile2 dg-skeleton-tile" style={{ height: 130 }}>
          <Skeleton width={110} height={14} style={{ marginBottom: 12 }} />
          <Skeleton width={50} height={32} style={{ marginBottom: 10 }} />
          <Skeleton width="80%" height={12} />
        </div>
        <div className="dg-tile2 dg-skeleton-tile" style={{ height: 130 }}>
          <Skeleton width={130} height={14} style={{ marginBottom: 12 }} />
          <Skeleton width={50} height={32} style={{ marginBottom: 10 }} />
          <Skeleton width="80%" height={12} />
        </div>
        <div className="dg-tile2 dg-skeleton-tile" style={{ height: 130 }}>
          <Skeleton width={100} height={14} style={{ marginBottom: 12 }} />
          <Skeleton width={50} height={32} style={{ marginBottom: 10 }} />
          <Skeleton width="80%" height={12} />
        </div>
      </div>
    </div>
  );
}

/** Living skeleton matching My Work list layout. */
export function MyWorkSkeleton() {
  return (
    <div className="dg-page-enter" role="status" aria-label="Loading your tasks">
      <header className="dg-hero">
        <div className="dg-hero__text">
          <Skeleton width={140} height={12} className="dg-skeleton-text--eyebrow" />
          <Skeleton width={180} height={32} className="dg-skeleton-text--title" />
          <Skeleton width={260} height={16} className="dg-skeleton-text--subline" />
        </div>
      </header>

      <div className="dg-tasklist" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div className="dg-skeleton-row" style={{ height: 68 }}>
          <Skeleton width={32} height={32} className="dg-skeleton-tile" />
          <div style={{ flex: 1 }}>
            <Skeleton width="45%" height={18} style={{ marginBottom: 6 }} />
            <Skeleton width="25%" height={13} />
          </div>
          <Skeleton width={110} height={24} className="dg-skeleton-pill" />
        </div>
        <div className="dg-skeleton-row" style={{ height: 68 }}>
          <Skeleton width={32} height={32} className="dg-skeleton-tile" />
          <div style={{ flex: 1 }}>
            <Skeleton width="50%" height={18} style={{ marginBottom: 6 }} />
            <Skeleton width="30%" height={13} />
          </div>
          <Skeleton width={110} height={24} className="dg-skeleton-pill" />
        </div>
        <div className="dg-skeleton-row" style={{ height: 68 }}>
          <Skeleton width={32} height={32} className="dg-skeleton-tile" />
          <div style={{ flex: 1 }}>
            <Skeleton width="38%" height={18} style={{ marginBottom: 6 }} />
            <Skeleton width="20%" height={13} />
          </div>
          <Skeleton width={110} height={24} className="dg-skeleton-pill" />
        </div>
      </div>
    </div>
  );
}

/** Living skeleton matching Exceptions Inbox split view. */
export function ExceptionsInboxSkeleton() {
  return (
    <div className="dg-inbox-layout" role="status" aria-label="Loading exceptions" style={{ marginTop: 16 }}>
      {/* Left List Column */}
      <section className="dg-inbox-list" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div className="dg-skeleton-tile" style={{ height: 84 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <Skeleton width={70} height={18} className="dg-skeleton-pill" />
            <Skeleton width={50} height={12} />
          </div>
          <Skeleton width="80%" height={16} style={{ marginBottom: 6 }} />
          <Skeleton width="50%" height={12} />
        </div>
        <div className="dg-skeleton-tile" style={{ height: 84 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <Skeleton width={70} height={18} className="dg-skeleton-pill" />
            <Skeleton width={50} height={12} />
          </div>
          <Skeleton width="75%" height={16} style={{ marginBottom: 6 }} />
          <Skeleton width="45%" height={12} />
        </div>
        <div className="dg-skeleton-tile" style={{ height: 84 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <Skeleton width={70} height={18} className="dg-skeleton-pill" />
            <Skeleton width={50} height={12} />
          </div>
          <Skeleton width="65%" height={16} style={{ marginBottom: 6 }} />
          <Skeleton width="40%" height={12} />
        </div>
      </section>

      {/* Right Inspector Column */}
      <aside className="dg-inbox-inspector" style={{ flex: 1, padding: 24 }}>
        <div className="dg-skeleton-card" style={{ height: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <Skeleton width={120} height={24} className="dg-skeleton-pill" />
            <Skeleton width={80} height={14} />
          </div>
          <Skeleton width="70%" height={26} />
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <Skeleton width="100%" height={14} />
            <Skeleton width="90%" height={14} />
            <Skeleton width="75%" height={14} />
          </div>
          <div style={{ marginTop: "auto", display: "flex", gap: 10 }}>
            <Skeleton width={110} height={36} className="dg-skeleton-btn" />
            <Skeleton width={110} height={36} className="dg-skeleton-btn" />
          </div>
        </div>
      </aside>
    </div>
  );
}

/** Living skeleton matching Adoption Overview layout. */
export function AdoptionSkeleton() {
  return (
    <div className="dg-adoption dg-page-enter" role="status" aria-label="Loading adoption metrics">
      <header className="dg-adoption__header">
        <div className="dg-adoption__header-titles">
          <Skeleton width={150} height={12} className="dg-skeleton-text--eyebrow" />
          <Skeleton width={320} height={32} className="dg-skeleton-text--title" />
          <Skeleton width={480} height={16} className="dg-skeleton-text--subline" />
        </div>
      </header>

      <div className="dg-skeleton-card" style={{ padding: 24, marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <div>
            <Skeleton width={140} height={14} style={{ marginBottom: 8 }} />
            <Skeleton width={90} height={36} />
          </div>
          <Skeleton width={140} height={40} className="dg-skeleton-pill" />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          <Skeleton height={60} className="dg-skeleton-tile" />
          <Skeleton height={60} className="dg-skeleton-tile" />
          <Skeleton height={60} className="dg-skeleton-tile" />
          <Skeleton height={60} className="dg-skeleton-tile" />
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <Skeleton height={44} className="dg-skeleton-row" />
        <Skeleton height={44} className="dg-skeleton-row" />
        <Skeleton height={44} className="dg-skeleton-row" />
      </div>
    </div>
  );
}
