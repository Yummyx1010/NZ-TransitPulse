interface AttributionProps {
  text?: string;
}

export function Attribution({ text }: AttributionProps) {
  return (
    <footer className="attribution">
      <span>
        {text ?? "Data source: Auckland Transport, licensed under CC BY 4.0"}
      </span>
      <span>Map &copy; OpenStreetMap contributors</span>
      <span>Independent project, not affiliated with Auckland Transport</span>
    </footer>
  );
}
