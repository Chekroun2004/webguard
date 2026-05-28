import { useState } from "react";
import { Loader2, Trash2 } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import {
  useCreateScheduledScan,
  useDeleteScheduledScan,
  useScheduledScansList,
  useUpdateScheduledScan,
  type ScheduledScan,
} from "@/hooks/useScheduledScans";
import { ApiError } from "@/lib/api";
import { describeCron, presetToCron, type Preset } from "@/lib/cron-presets";

// ── Add scheduled scan form ──────────────────────────────────────────────────

function AddScheduledScanForm() {
  const [url, setUrl] = useState("");
  const [kind, setKind] = useState<Preset["kind"]>("daily");
  const [hour, setHour] = useState(9);
  const [weekDay, setWeekDay] = useState(1);
  const [monthDay, setMonthDay] = useState(1);
  const [advanced, setAdvanced] = useState(false);
  const [customCron, setCustomCron] = useState("0 9 * * *");
  const [error, setError] = useState<string | null>(null);

  const create = useCreateScheduledScan();

  const computedCron = advanced
    ? customCron
    : presetToCron(
        kind === "daily"
          ? { kind: "daily", hour }
          : kind === "weekly"
            ? { kind: "weekly", hour, weekDay }
            : { kind: "monthly", hour, monthDay },
      );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await create.mutateAsync({ url, cron_expression: computedCron });
      setUrl("");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erreur inattendue.");
    }
  };

  return (
    <div className="rounded-lg border bg-card p-6 space-y-4">
      <h2 className="font-semibold">Planifier un scan récurrent</h2>
      {error && (
        <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">{error}</p>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="url"
          required
          placeholder="https://example.com"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={create.isPending}
          className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
        />

        <div className="space-y-2">
          <label className="block text-sm font-medium">Fréquence</label>
          <div className="flex gap-3 text-sm">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="radio"
                name="kind"
                checked={kind === "daily"}
                onChange={() => setKind("daily")}
              />
              Quotidien
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="radio"
                name="kind"
                checked={kind === "weekly"}
                onChange={() => setKind("weekly")}
              />
              Hebdomadaire
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="radio"
                name="kind"
                checked={kind === "monthly"}
                onChange={() => setKind("monthly")}
              />
              Mensuel
            </label>
          </div>

          {!advanced && (
            <div className="flex gap-2 items-center text-sm">
              {kind === "weekly" && (
                <select
                  value={weekDay}
                  onChange={(e) => setWeekDay(Number(e.target.value))}
                  className="rounded-md border bg-background px-2 py-1"
                >
                  <option value={1}>Lundi</option>
                  <option value={2}>Mardi</option>
                  <option value={3}>Mercredi</option>
                  <option value={4}>Jeudi</option>
                  <option value={5}>Vendredi</option>
                  <option value={6}>Samedi</option>
                  <option value={0}>Dimanche</option>
                </select>
              )}
              {kind === "monthly" && (
                <select
                  value={monthDay}
                  onChange={(e) => setMonthDay(Number(e.target.value))}
                  className="rounded-md border bg-background px-2 py-1"
                >
                  {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => (
                    <option key={d} value={d}>
                      Jour {d}
                    </option>
                  ))}
                </select>
              )}
              <span>à</span>
              <select
                value={hour}
                onChange={(e) => setHour(Number(e.target.value))}
                className="rounded-md border bg-background px-2 py-1"
              >
                {Array.from({ length: 24 }, (_, i) => i).map((h) => (
                  <option key={h} value={h}>
                    {String(h).padStart(2, "0")}:00
                  </option>
                ))}
              </select>
            </div>
          )}

          <label className="flex items-center gap-1.5 cursor-pointer text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={advanced}
              onChange={(e) => setAdvanced(e.target.checked)}
            />
            Mode avancé (cron libre)
          </label>

          {advanced && (
            <input
              type="text"
              value={customCron}
              onChange={(e) => setCustomCron(e.target.value)}
              placeholder="0 9 * * 1,3,5"
              className="w-full rounded-md border bg-background px-3 py-2 text-sm font-mono"
            />
          )}

          <p className="text-xs text-muted-foreground">
            Aperçu : {describeCron(computedCron)}
          </p>
        </div>

        <button
          type="submit"
          disabled={create.isPending}
          className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center gap-1.5"
        >
          {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Planifier
        </button>
      </form>
    </div>
  );
}

// ── Schedule card ────────────────────────────────────────────────────────────

function ScheduleCard({ sched }: { sched: ScheduledScan }) {
  const toggle = useUpdateScheduledScan();
  const del = useDeleteScheduledScan();

  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      <div className="px-4 py-3 flex items-center justify-between gap-4">
        <div className="min-w-0 space-y-0.5">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm truncate">{sched.url}</span>
            {sched.is_active ? (
              <span className="text-xs rounded bg-green-500/15 text-green-600 px-1.5 py-0.5">
                actif
              </span>
            ) : (
              <span className="text-xs rounded bg-muted text-muted-foreground px-1.5 py-0.5">
                inactif
              </span>
            )}
          </div>
          <div className="text-xs text-muted-foreground">
            {describeCron(sched.cron_expression)}
          </div>
          <div className="text-xs text-muted-foreground">
            Prochain : {new Date(sched.next_run_at).toLocaleString("fr-FR")}
            {sched.last_run_at && (
              <>
                {" • "}Dernier : {new Date(sched.last_run_at).toLocaleString("fr-FR")}
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() =>
              toggle.mutate({
                id: sched.id,
                body: { is_active: !sched.is_active },
              })
            }
            disabled={toggle.isPending}
            className="text-xs rounded-md border px-2 py-1 hover:bg-muted disabled:opacity-50"
          >
            {sched.is_active ? "Désactiver" : "Activer"}
          </button>
          <button
            onClick={() => del.mutate(sched.id)}
            disabled={del.isPending}
            className="text-xs rounded-md border px-2 py-1 hover:bg-destructive/10 hover:text-destructive disabled:opacity-50 flex items-center gap-1"
            aria-label="Supprimer"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export function ScheduledScansPage() {
  const { data: schedules, isLoading } = useScheduledScansList();

  return (
    <AppShell>
      <main className="container py-8 space-y-8 max-w-2xl">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Scans planifiés</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Configurez des scans récurrents sur vos domaines vérifiés.
          </p>
        </div>

        <AddScheduledScanForm />

        <div className="space-y-3">
          <h2 className="font-semibold">Schedules existants</h2>
          {isLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="h-4 w-4 animate-spin" /> Chargement…
            </div>
          ) : !schedules || schedules.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Aucun schedule. Ajoutez-en un ci-dessus.
            </p>
          ) : (
            <div className="space-y-2">
              {schedules.map((s) => (
                <ScheduleCard key={s.id} sched={s} />
              ))}
            </div>
          )}
        </div>
      </main>
    </AppShell>
  );
}
