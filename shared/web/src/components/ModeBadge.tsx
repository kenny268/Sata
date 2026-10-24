/** **A-MOD-04** — LIVE red, SIM blue. */

type Props = { mode: string; tag: string; color: string };

export function ModeBadge({ mode, tag, color }: Props) {
  const className = color === "red" ? "badge-live" : "badge-sim";
  return (
    <span className={className} title={mode}>
      {tag}
    </span>
  );
}
