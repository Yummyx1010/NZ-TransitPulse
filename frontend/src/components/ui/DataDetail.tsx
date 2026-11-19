export interface DetailField {
  label: string;
  value: string;
}

export function DataDetail({
  title,
  fields,
  onClear,
}: {
  title: string;
  fields: DetailField[];
  onClear?: () => void;
}) {
  return (
    <div className="observatory-selected" aria-live="polite">
      <strong>{title}</strong>
      {fields.map((field) => (
        <span key={field.label}>
          {field.label}: <strong>{field.value}</strong>
        </span>
      ))}
      {onClear ? (
        <button type="button" className="observatory-clear" onClick={onClear}>
          Clear selection
        </button>
      ) : null}
    </div>
  );
}
