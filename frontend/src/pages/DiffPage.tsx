import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, GitCompare, Loader2, ShieldCheck } from "lucide-react";

import { SeverityBadge } from "@/components/SeverityBadge";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useScanList } from "@/hooks/useScan";
import { useScanDiff } from "@/hooks/useScanDiff";
import type { Scan, Vulnerability } from "@/types";

function formatUrl(url: string): string {
  return url.replace(/\/$/, "");
}

function VulnList({ items, emptyMessage }: { items: Vulnerability[]; emptyMessage: string }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground py-4 text-center">{emptyMessage}</p>;
  }
  return (
    <ul className="space-y-2">
      {items.map((v) => (
        <li
          key={`${v.id}-${v.name}`}
          className="rounded-md border bg-card p-3 flex items-start gap-3"
        >
          <SeverityBadge severity={v.severity} />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium">{v.name}</p>
            {v.evidence && (
              <p className="text-xs font-mono text-muted-foreground truncate mt-0.5">
                {v.evidence}
              </p>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

export function DiffPage() {
  const { data: scans, isLoading: scansLoading } = useScanList();
  const [oldId, setOldId] = useState<number | null>(null);
  const [newId, setNewId] = useState<number | null>(null);

  // Only completed scans can be diffed
  const completedScans = useMemo(
    () => (scans ?? []).filter((s) => s.status === "completed"),
    [scans],
  );

  // Group scans by normalized URL for the dropdowns
  const scansByUrl = useMemo(() => {
    const map = new Map<string, Scan[]>();
    for (const s of completedScans) {
      const k = formatUrl(s.url);
      const list = map.get(k) ?? [];
      list.push(s);
      map.set(k, list);
    }
    return map;
  }, [completedScans]);

  // For the "new" dropdown, only show scans whose URL has at least 2 entries OR matches the selected "old"
  const oldScan = completedScans.find((s) => s.id === oldId) ?? null;
  const compatibleScans = oldScan
    ? completedScans.filter((s) => formatUrl(s.url) === formatUrl(oldScan.url) && s.id !== oldId)
    : completedScans;

  const { data: diff, isLoading: diffLoading, error } = useScanDiff(oldId, newId);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container flex h-14 items-center justify-between">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <span className="font-semibold">
              <span className="text-[#6366f1]">Web</span>Guard
            </span>
            <span className="text-muted-foreground">/</span>
            <span className="text-sm">Comparer des scans</span>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link
              to="/dashboard"
              className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Tableau de bord
            </Link>
          </div>
        </div>
      </header>

      <main className="container py-8 space-y-6 max-w-5xl">
        <div className="space-y-1">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <GitCompare className="h-5 w-5 text-[#6366f1]" />
            Comparer deux scans
          </h1>
          <p className="text-sm text-muted-foreground">
            Sélectionnez deux scans complétés du même domaine pour voir ce qui a changé.
          </p>
        </div>

        {/* Selectors */}
        <div className="grid sm:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Scan de référence</label>
            <select
              value={oldId ?? ""}
              onChange={(e) => {
                const v = e.target.value ? parseInt(e.target.value, 10) : null;
                setOldId(v);
                if (newId !== null) setNewId(null);
              }}
              disabled={scansLoading || completedScans.length === 0}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm disabled:opacity-50"
            >
              <option value="">— Choisir un scan —</option>
              {Array.from(scansByUrl.entries()).map(([url, list]) => (
                <optgroup key={url} label={url}>
                  {list.map((s) => (
                    <option key={s.id} value={s.id}>
                      #{s.id} — {new Date(s.created_at).toLocaleString("fr-FR")}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Scan à comparer</label>
            <select
              value={newId ?? ""}
              onChange={(e) => setNewId(e.target.value ? parseInt(e.target.value, 10) : null)}
              disabled={oldId === null || compatibleScans.length === 0}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm disabled:opacity-50"
            >
              <option value="">— Choisir un scan —</option>
              {compatibleScans.map((s) => (
                <option key={s.id} value={s.id}>
                  #{s.id} — {new Date(s.created_at).toLocaleString("fr-FR")}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Empty state */}
        {!scansLoading && completedScans.length < 2 && (
          <p className="text-sm text-muted-foreground py-8 text-center border rounded-md">
            Vous devez avoir au moins deux scans complétés sur un même domaine pour utiliser cette
            fonctionnalité.
          </p>
        )}

        {/* Diff results */}
        {diffLoading && (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {error && (
          <p className="text-sm text-red-600 py-4">
            Erreur : impossible de comparer ces deux scans.
          </p>
        )}

        {diff && (
          <>
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-lg border bg-red-50 dark:bg-red-950/40 p-4 text-center">
                <p className="text-2xl font-bold text-red-700 dark:text-red-300">
                  {diff.added.length}
                </p>
                <p className="text-xs text-red-600 dark:text-red-400 uppercase tracking-wide mt-1">
                  Nouvelles vulnérabilités
                </p>
              </div>
              <div className="rounded-lg border bg-green-50 dark:bg-green-950/40 p-4 text-center">
                <p className="text-2xl font-bold text-green-700 dark:text-green-300">
                  {diff.removed.length}
                </p>
                <p className="text-xs text-green-600 dark:text-green-400 uppercase tracking-wide mt-1">
                  Corrigées
                </p>
              </div>
              <div className="rounded-lg border bg-muted p-4 text-center">
                <p className="text-2xl font-bold text-foreground">{diff.unchanged.length}</p>
                <p className="text-xs text-muted-foreground uppercase tracking-wide mt-1">
                  Inchangées
                </p>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <h2 className="font-semibold text-sm mb-2 text-red-700 dark:text-red-400">
                  Nouvelles vulnérabilités ({diff.added.length})
                </h2>
                <VulnList
                  items={diff.added}
                  emptyMessage="Aucune nouvelle vulnérabilité — bonne nouvelle !"
                />
              </div>
              <div>
                <h2 className="font-semibold text-sm mb-2 text-green-700 dark:text-green-400">
                  Vulnérabilités corrigées ({diff.removed.length})
                </h2>
                <VulnList items={diff.removed} emptyMessage="Aucune correction détectée." />
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
