export function DataSourceNote({ children }: { children: React.ReactNode }) {
  return <p className="observatory-note">{children}</p>;
}

export function DataWarning({ children }: { children: React.ReactNode }) {
  return <p className="observatory-note is-warning">{children}</p>;
}
