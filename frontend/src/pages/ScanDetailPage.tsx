import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Download, FileJson, FileText, Loader2, ShieldCheck } from "lucide-react";
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import { SeverityBadge } from "@/components/SeverityBadge";
import { useScan } from "@/hooks/useScan";
import { tokenStorage } from "@/lib/auth";
import type { Vulnerability } from "@/types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"] as const;
type Severity = (typeof SEVERITY_ORDER)[number];

const SEVERITY_COLORS: Record<Severity, string> = {
  critical: "#dc2626",
  high: "#ea580c",
  medium: "#d97706",
  low: "#16a34a",
  info: "#2563eb",
};

const SEVERITY_LABELS: Record<Severity, string> = {
  critical: "Critique",
  high: "Élevée",
  medium: "Moyenne",
  low: "Faible",
  info: "Info",
};

function triggerDownload(blob: Blob, filename: string) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function downloadFile(url: string, filename: string) {
  const token = tokenStorage.getAccess();
  fetch(`${BASE_URL}${url}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
    .then((r) => r.blob())
    .then((blob) => triggerDownload(blob, filename));
}

function downloadJson(url: string, filename: string) {
  const token = tokenStorage.getAccess();
  fetch(`${BASE_URL}${url}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
    .then((r) => r.json())
    .then((data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      triggerDownload(blob, filename);
    });
}

function SeverityChart({ findings }: { findings: Vulnerability[] }) {
  const data = SEVERITY_ORDER.map((sev) => ({
    name: SEVERITY_LABELS[sev],
    value: findings.filter((f) => f.severity === sev).length,
    color: SEVERITY_COLORS[sev],
  })).filter((d) => d.value > 0);

  if (data.length === 0) return null;

  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className="font-semibold text-sm mb-3">Répartition par sévérité</h3>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={80}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => [
              typeof value === "number" ? value : 0,
              "vulnérabilité(s)",
            ]}
          />
          <Legend
            formatter={(value) => (
              <span className="text-xs text-muted-foreground">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

function FindingCard({ finding }: { finding: Vulnerability }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-muted/40 transition-colors"
      >
        <SeverityBadge severity={finding.severity} />
        <span className="text-sm font-medium flex-1">{finding.name}</span>
        <span className="text-muted-foreground text-xs">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="px-4 py-3 border-t space-y-2 text-sm">
          <p className="text-muted-foreground">{finding.description}</p>
          {finding.recommendation && (
            <p>
              <span className="font-medium text-xs uppercase tracking-wide text-muted-foreground">
                Recommandation :
              </span>{" "}
              {finding.recommendation}
            </p>
          )}
          {finding.evidence && (
            <pre className="text-xs font-mono bg-muted px-3 py-2 rounded overflow-x-auto whitespace-pre-wrap break-all">
              {finding.evidence}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

export function ScanDetailPage() {
  const { id } = useParams<{ id: string }>();
  const scanId = id ? parseInt(id, 10) : null;
  const { data: scan, isLoading } = useScan(scanId);

  const [activeFilter, setActiveFilter] = useState<Severity | "all">("all");

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4">
        <p className="text-muted-foreground">Scan introuvable.</p>
        <Link to="/dashboard" className="text-sm text-primary hover:underline">
          Retour au tableau de bord
        </Link>
      </div>
    );
  }

  const filteredFindings =
    activeFilter === "all"
      ? scan.findings
      : scan.findings.filter((f) => f.severity === activeFilter);

  const countBySev = SEVERITY_ORDER.reduce<Record<string, number>>((acc, s) => {
    acc[s] = scan.findings.filter((f) => f.severity === s).length;
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container flex h-14 items-center justify-between">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <span className="font-semibold"><span className="text-[#6366f1]">Web</span>Guard</span>
          </div>
          <Link
            to="/dashboard"
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Tableau de bord
          </Link>
        </div>
      </header>

      <main className="container py-8 space-y-6 max-w-4xl">
        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-xl font-bold break-all">{scan.url}</h1>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span>{new Date(scan.created_at).toLocaleString("fr-FR")}</span>
            <span className="capitalize font-medium">{scan.status}</span>
            <span>{scan.findings.length} vulnérabilité(s)</span>
          </div>
        </div>

        {/* Download buttons */}
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() =>
              downloadJson(`/api/v1/scans/${scan.id}/report`, `webguard-${scan.id}.json`)
            }
            className="flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm hover:bg-muted transition-colors"
          >
            <FileJson className="h-4 w-4" />
            Exporter JSON
          </button>
          <button
            onClick={() =>
              downloadFile(
                `/api/v1/scans/${scan.id}/report.pdf`,
                `webguard-report-${scan.id}.pdf`,
              )
            }
            className="flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm hover:bg-muted transition-colors"
          >
            <Download className="h-4 w-4" />
            <FileText className="h-4 w-4 -ml-0.5" />
            Exporter PDF
          </button>
        </div>

        {/* Chart */}
        {scan.findings.length > 0 && <SeverityChart findings={scan.findings} />}

        {/* Severity filters */}
        {scan.findings.length > 0 && (
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => setActiveFilter("all")}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors border ${
                activeFilter === "all"
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-background text-muted-foreground border-border hover:border-foreground"
              }`}
            >
              Tout ({scan.findings.length})
            </button>
            {SEVERITY_ORDER.map(
              (sev) =>
                countBySev[sev] > 0 && (
                  <button
                    key={sev}
                    onClick={() => setActiveFilter(sev)}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition-colors border ${
                      activeFilter === sev
                        ? "bg-primary text-primary-foreground border-primary"
                        : "bg-background text-muted-foreground border-border hover:border-foreground"
                    }`}
                  >
                    {SEVERITY_LABELS[sev]} ({countBySev[sev]})
                  </button>
                ),
            )}
          </div>
        )}

        {/* Findings list */}
        <div className="space-y-2">
          <h2 className="font-semibold text-sm">
            {filteredFindings.length} résultat(s)
            {activeFilter !== "all" && ` — ${SEVERITY_LABELS[activeFilter]}`}
          </h2>
          {filteredFindings.length === 0 ? (
            <p className="text-sm text-green-600 font-medium py-4 text-center">
              ✓ Aucune vulnérabilité détectée
            </p>
          ) : (
            filteredFindings.map((f) => <FindingCard key={f.id} finding={f} />)
          )}
        </div>
      </main>
    </div>
  );
}
