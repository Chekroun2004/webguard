import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Loader2, ScrollText, ShieldCheck } from "lucide-react";

import { ThemeToggle } from "@/components/ThemeToggle";
import { useAuditEvents } from "@/hooks/useAudit";
import { ACTION_LABELS } from "@/types/audit";
import type { AuditAction, AuditFilters } from "@/types/audit";

// ── Helpers ────────────────────────────────────────────────────────────────

const dateFormatter = new Intl.DateTimeFormat("fr-FR", {
  dateStyle: "medium",
  timeStyle: "short",
});

function actionBadgeClass(action: AuditAction): string {
  if (action.endsWith(".create")) return "bg-[#6366f1]/15 text-[#6366f1]";
  if (action.endsWith(".delete") || action.endsWith(".revoke"))
    return "bg-destructive/10 text-destructive";
  if (action.endsWith(".update")) return "bg-amber-500/15 text-amber-600";
  if (action.endsWith(".test") || action.endsWith(".enable"))
    return "bg-emerald-500/15 text-emerald-600";
  if (action.endsWith(".disable")) return "bg-muted text-muted-foreground";
  return "bg-muted text-muted-foreground";
}

// ── Page ───────────────────────────────────────────────────────────────────

export function AuditPage() {
  const [filters, setFilters] = useState<AuditFilters>({ page: 1, pageSize: 50 });
  const { data, isLoading } = useAuditEvents(filters);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container flex h-14 items-center justify-between">
          <div className="flex items-center gap-4">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <span className="font-semibold">
              <span className="text-[#6366f1]">Web</span>Guard
            </span>
            <span className="text-muted-foreground">/</span>
            <span className="text-sm">Journal d'activité</span>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="container py-10 space-y-8 max-w-5xl">
        <div className="flex items-center gap-3">
          <Link
            to="/dashboard"
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Tableau de bord
          </Link>
        </div>

        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ScrollText className="h-6 w-6 text-[#6366f1]" />
            Journal d'activité
          </h1>
          <p className="text-muted-foreground mt-1">
            Historique des actions sensibles sur votre compte (scans, clés API,
            webhooks, 2FA…).
          </p>
        </div>

        {/* Filters */}
        <div className="rounded-lg border bg-card p-6">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">Action</label>
              <select
                value={filters.action ?? ""}
                onChange={(e) =>
                  setFilters((f) => ({
                    ...f,
                    page: 1,
                    action: e.target.value
                      ? (e.target.value as AuditAction)
                      : undefined,
                  }))
                }
                className="rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">Toutes les actions</option>
                {Object.entries(ACTION_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">Statut</label>
              <select
                value={filters.status ?? ""}
                onChange={(e) =>
                  setFilters((f) => ({
                    ...f,
                    page: 1,
                    status:
                      e.target.value === "success" || e.target.value === "failure"
                        ? e.target.value
                        : undefined,
                  }))
                }
                className="rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">Tous</option>
                <option value="success">Succès</option>
                <option value="failure">Échec</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">Du</label>
              <input
                type="date"
                value={filters.dateFrom ?? ""}
                onChange={(e) =>
                  setFilters((f) => ({
                    ...f,
                    page: 1,
                    dateFrom: e.target.value || undefined,
                  }))
                }
                className="rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">Au</label>
              <input
                type="date"
                value={filters.dateTo ?? ""}
                onChange={(e) =>
                  setFilters((f) => ({
                    ...f,
                    page: 1,
                    dateTo: e.target.value || undefined,
                  }))
                }
                className="rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            <button
              onClick={() => setFilters({ page: 1, pageSize: 50 })}
              className="rounded-md border px-3 py-2 text-sm hover:bg-muted transition-colors"
            >
              Réinitialiser
            </button>
          </div>
        </div>

        {/* Table */}
        <div className="rounded-lg border bg-card p-6">
          {isLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Chargement…
            </div>
          ) : !data || data.total === 0 ? (
            <p className="text-sm text-muted-foreground">
              Aucune activité enregistrée.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left text-muted-foreground text-xs uppercase font-medium py-2 pr-4">
                      Date
                    </th>
                    <th className="text-left text-muted-foreground text-xs uppercase font-medium py-2 pr-4">
                      Action
                    </th>
                    <th className="text-left text-muted-foreground text-xs uppercase font-medium py-2 pr-4">
                      Cible
                    </th>
                    <th className="text-left text-muted-foreground text-xs uppercase font-medium py-2 pr-4">
                      Statut
                    </th>
                    <th className="text-left text-muted-foreground text-xs uppercase font-medium py-2 pr-4">
                      IP
                    </th>
                    <th className="text-left text-muted-foreground text-xs uppercase font-medium py-2">
                      Agent
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((e) => (
                    <tr key={e.id} className="border-b last:border-0">
                      <td className="py-2 pr-4 whitespace-nowrap">
                        {dateFormatter.format(new Date(e.created_at))}
                      </td>
                      <td className="py-2 pr-4">
                        <span
                          className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${actionBadgeClass(
                            e.action,
                          )}`}
                        >
                          {ACTION_LABELS[e.action]}
                        </span>
                      </td>
                      <td className="py-2 pr-4 whitespace-nowrap">
                        {e.target_type ? `${e.target_type} #${e.target_id}` : "—"}
                      </td>
                      <td className="py-2 pr-4">
                        {e.status === "success" ? (
                          <span className="inline-block rounded px-1.5 py-0.5 text-xs font-medium bg-green-500/15 text-green-600">
                            Succès
                          </span>
                        ) : (
                          <span className="inline-block rounded px-1.5 py-0.5 text-xs font-medium bg-destructive/10 text-destructive">
                            Échec
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-4">
                        <span className="font-mono text-xs">{e.ip ?? "—"}</span>
                      </td>
                      <td className="py-2">
                        <span
                          className="truncate max-w-[12rem] inline-block align-bottom"
                          title={e.user_agent ?? ""}
                        >
                          {e.user_agent ?? "—"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Pagination */}
        {data && data.total > 0 && (
          <div className="flex items-center justify-between gap-4">
            <button
              onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}
              disabled={filters.page <= 1}
              className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Précédent
            </button>
            <span className="text-sm text-muted-foreground">
              Page {data.page} sur {totalPages}
            </span>
            <button
              onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
              disabled={filters.page >= totalPages}
              className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Suivant
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
