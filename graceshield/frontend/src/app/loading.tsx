export default function Loading() {
  return (
    <div className="wrap loading-page" role="status" aria-label="Loading GraceShield">
      <div className="skeleton skeleton-title" />
      <div className="product-grid">
        {[1, 2, 3, 4].map((n) => (
          <div key={n} className="skeleton skeleton-card" />
        ))}
      </div>
      <span className="sr-only">Loading your next chapter…</span>
    </div>
  );
}
