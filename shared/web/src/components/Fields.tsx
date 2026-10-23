export function Fields({ rows }: { rows: Array<[string, string]> }) {
  return (
    <dl className="fields">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
