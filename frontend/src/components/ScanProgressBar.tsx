type Status = "pending" | "running" | "completed" | "failed" | null;

const STATUS_LABEL: Record<NonNullable<Status>, string> = {
  pending: "En attente…",
  running: "Scan en cours…",
  completed: "Terminé",
  failed: "Échec",
};

const STATUS_WIDTH: Record<NonNullable<Status>, string> = {
  pending: "w-1/4",
  running: "w-3/4",
  completed: "w-full",
  failed: "w-full",
};

const STATUS_COLOR: Record<NonNullable<Status>, string> = {
  pending: "bg-muted-foreground/40",
  running: "bg-primary",
  completed: "bg-green-500",
  failed: "bg-destructive",
};

export function ScanProgressBar({ status }: { status: Status }) {
  if (!status || status === "completed") return null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{STATUS_LABEL[status]}</span>
        {status === "running" && (
          <span className="animate-pulse">●</span>
        )}
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${STATUS_WIDTH[status]} ${STATUS_COLOR[status]}`}
        />
      </div>
    </div>
  );
}
