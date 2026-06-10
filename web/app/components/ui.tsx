// Shared presentational helpers reused across the upload, mandate, and run views.

export type Tone = "slate" | "green" | "red" | "amber" | "blue";

const TONES: Record<Tone, string> = {
  slate: "bg-slate-100 text-slate-700",
  green: "bg-green-100 text-green-700",
  red: "bg-red-100 text-red-700",
  amber: "bg-amber-100 text-amber-700",
  blue: "bg-blue-100 text-blue-700",
};

export function Badge({
  children,
  tone = "slate",
}: {
  children: React.ReactNode;
  tone?: Tone;
}) {
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}>
      {children}
    </span>
  );
}

export function format(v: unknown): string {
  if (v === null || v === undefined) return "—";
  return String(v);
}

export function Section({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <fieldset className="rounded-md border border-slate-200 p-4">
      <legend className="px-1 text-sm font-medium text-slate-700">{title}</legend>
      {hint && <p className="mb-2 text-xs text-slate-400">{hint}</p>}
      {children}
    </fieldset>
  );
}
