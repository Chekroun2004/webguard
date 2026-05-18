type Severity = "info" | "low" | "medium" | "high" | "critical";

const COLORS: Record<Severity, string> = {
  info: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200",
  low: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200",
  medium: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200",
  high: "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200",
  critical: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200",
};

const LABELS: Record<Severity, string> = {
  info: "Info",
  low: "Faible",
  medium: "Moyenne",
  high: "Élevée",
  critical: "Critique",
};

export function SeverityBadge({ severity }: { severity: Severity | string }) {
  const isKnown = (s: string): s is Severity => s in LABELS;
  const colorClass = isKnown(severity)
    ? COLORS[severity]
    : "bg-muted text-muted-foreground";
  const label = isKnown(severity) ? LABELS[severity] : severity;

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colorClass}`}
    >
      {label}
    </span>
  );
}
