export function EmptyState({ children }: { children: React.ReactNode }) {
  return <div className="observatory-empty">{children}</div>;
}

export function LoadingState({ label = "Loading data…" }: { label?: string }) {
  return <div className="observatory-loading" role="status">{label}</div>;
}
