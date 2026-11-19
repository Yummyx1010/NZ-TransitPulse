interface PageHeaderProps {
  title: string;
  description: string;
  meta?: string[];
}

export function PageHeader({ title, description, meta = [] }: PageHeaderProps) {
  return (
    <header className="observatory-page-header">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {meta.length > 0 ? (
        <div className="observatory-page-meta" aria-label="Page metadata">
          {meta.map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      ) : null}
    </header>
  );
}
