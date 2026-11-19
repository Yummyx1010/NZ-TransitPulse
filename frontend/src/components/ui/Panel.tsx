interface PanelProps {
  title: string;
  subtitle?: string;
  meta?: string;
  children: React.ReactNode;
}

export function Panel({ title, subtitle, meta, children }: PanelProps) {
  return (
    <section className="observatory-panel">
      <div className="observatory-panel-header">
        <div>
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        {meta ? <div className="observatory-panel-meta">{meta}</div> : null}
      </div>
      <div className="observatory-panel-body">{children}</div>
    </section>
  );
}
