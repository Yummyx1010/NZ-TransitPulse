export interface MetricStripItem {
  label: string;
  value: string;
  note?: string;
}

export function MetricStrip({ items }: { items: MetricStripItem[] }) {
  return (
    <div className="observatory-metric-strip" aria-label="Summary metrics">
      {items.map((item) => (
        <div className="observatory-metric" key={item.label}>
          <p className="observatory-metric-label">{item.label}</p>
          <strong className="observatory-metric-value">{item.value}</strong>
          {item.note ? (
            <span className="observatory-metric-note">{item.note}</span>
          ) : null}
        </div>
      ))}
    </div>
  );
}
