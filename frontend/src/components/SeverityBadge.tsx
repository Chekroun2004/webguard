type Severity = "info" | "low" | "medium" | "high" | "critical";

const COLORS: Record<Severity, string> = {
  info: "bg-blue-100 text-blue-800",
  low: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${COLORS[severity] ?? "bg-muted text-muted-foreground"}`}
    >
      {severity}
    </span>
  );
}
