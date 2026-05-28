import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Download, FileJson, FileText, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import { AppShell } from "@/components/AppShell";
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
  const { t } = useTranslation();

  const data = SEVERITY_ORDER.map((sev) => ({
    name: t(`severity.${sev}`),
    value: findings.filter((f) => f.severity === sev).length,
    color: SEVERITY_COLORS[sev],
  })).filter((d) => d.value > 0);

  if (data.length === 0) return null;

  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className="font-semibold text-sm mb-3">{t("scan_detail.severity_chart")}</h3>
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
              t("scan_detail.vuln_plural"),
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
  const { t } = useTranslation();

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
                {t("scan_detail.recommendation")}
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
  const { t, i18n } = useTranslation();
  const locale = i18n.language === "fr" ? "fr-FR" : "en-US";

  const [activeFilter, setActiveFilter] = useState<Severity | "all">("all");

  if (isLoading) {
    return (
      <AppShell>
        <div className="flex-1 flex items-center justify-center py-24">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  if (!scan) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <p className="text-muted-foreground">{t("scan_detail.not_found")}</p>
          <Link to="/dashboard" className="text-sm text-primary hover:underline">
            {t("scan_detail.back_dashboard")}
          </Link>
        </div>
      </AppShell>
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
    <AppShell>
      <main className="container py-8 space-y-6 max-w-4xl">
        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-xl font-bold break-all">{scan.url}</h1>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span>{new Date(scan.created_at).toLocaleString(locale)}</span>
            <span className="capitalize font-medium">{scan.status}</span>
            <span>
              {scan.findings.length} {t("scan_detail.vuln_plural")}
            </span>
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
            {t("scan_detail.export_json")}
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
            {t("scan_detail.export_pdf")}
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
              {t("scan_detail.filter_all", { count: scan.findings.length })}
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
                    {t(`severity.${sev}`)} ({countBySev[sev]})
                  </button>
                ),
            )}
          </div>
        )}

        {/* Findings list */}
        <div className="space-y-2">
          <h2 className="font-semibold text-sm">
            {t("scan_detail.result_count", { count: filteredFindings.length })}
            {activeFilter !== "all" && ` — ${t(`severity.${activeFilter}`)}`}
          </h2>
          {filteredFindings.length === 0 ? (
            <p className="text-sm text-green-600 font-medium py-4 text-center">
              {t("scan_detail.no_findings")}
            </p>
          ) : (
            filteredFindings.map((f) => <FindingCard key={f.id} finding={f} />)
          )}
        </div>
      </main>
    </AppShell>
  );
}
