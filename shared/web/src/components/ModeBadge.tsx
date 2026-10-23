/** **A-MOD-04** — LIVE red, SIM blue. */

type Props = { mode: string; tag: string; color: string };

export function ModeBadge({ mode, tag, color }: Props) {
  const tone =
    color === "red"
      ? "border-rose-200 bg-rose-50 text-rose-700"
      : color === "amber"
        ? "border-amber-200 bg-amber-50 text-amber-800"
        : "border-blue-200 bg-blue-50 text-blue-700";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 font-mono text-xs sm:text-sm ${tone}`}
      title={mode}
    >
      {tag}
    </span>
  );
}
