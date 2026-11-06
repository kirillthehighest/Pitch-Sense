// Loading placeholders shaped like what is coming (Phase 25): rows of a match list, a card, a
// table, so the screen keeps its layout while the server answers. They pulse gently, and stay
// still for readers who asked for less motion.

export function SkeletonLine({ width = "100%", height = 14 }: { width?: number | string; height?: number }) {
  return <span className="skeleton" style={{ width, height }} />;
}

export function SkeletonRows({ rows = 4, label = "Se încarcă…" }: { rows?: number; label?: string }) {
  return (
    <div className="skeleton-rows" role="status" aria-label={label}>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="skeleton-row">
          <SkeletonLine width={40} />
          <span className="skeleton-teams">
            <span className="skeleton-disc" />
            <SkeletonLine width="34%" />
            <SkeletonLine width={26} />
            <SkeletonLine width="34%" />
            <span className="skeleton-disc" />
          </span>
          <span className="skeleton-chips">
            <SkeletonLine width={56} height={30} />
            <SkeletonLine width={56} height={30} />
            <SkeletonLine width={56} height={30} />
          </span>
        </div>
      ))}
    </div>
  );
}

export function SkeletonCard({ height = 220, title = true }: { height?: number; title?: boolean }) {
  return (
    <section className="card skeleton-card" role="status" aria-label="Se încarcă…">
      {title && <SkeletonLine width="38%" height={18} />}
      <span className="skeleton block" style={{ height }} />
    </section>
  );
}

export function SkeletonTable({ rows = 8 }: { rows?: number }) {
  return (
    <section className="card skeleton-card" role="status" aria-label="Se încarcă…">
      <SkeletonLine width="30%" height={18} />
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="skeleton-table-row">
          <SkeletonLine width={22} />
          <span className="skeleton-disc" />
          <SkeletonLine width="28%" />
          <span className="grow" />
          <SkeletonLine width="34%" />
        </div>
      ))}
    </section>
  );
}
