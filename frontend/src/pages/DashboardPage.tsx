import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, Loader2, ScanLine } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useCreateScan, useScanList, type ScanAuthConfig } from "@/hooks/useScan";
import { useScanEvents } from "@/hooks/useScanEvents";
import { SeverityBadge } from "@/components/SeverityBadge";
import { ScanProgressBar } from "@/components/ScanProgressBar";
import { AppShell } from "@/components/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api";
import type { Scan } from "@/types";

// ── Scan form ─────────────────────────────────────────────────────────────────

type AuthMode = "none" | "cookie" | "form_login";

function ScanForm() {
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [activeScanId, setActiveScanId] = useState<number | null>(null);

  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>("none");
  const [cookieName, setCookieName] = useState("");
  const [cookieValue, setCookieValue] = useState("");
  const [loginUrl, setLoginUrl] = useState("");
  const [usernameField, setUsernameField] = useState("username");
  const [passwordField, setPasswordField] = useState("password");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const createScan = useCreateScan();
  const liveStatus = useScanEvents(activeScanId);
  const { t } = useTranslation();

  useEffect(() => {
    if (liveStatus === "completed" || liveStatus === "failed") {
      const timer = setTimeout(() => setActiveScanId(null), 2500);
      return () => clearTimeout(timer);
    }
  }, [liveStatus]);

  const buildAuthConfig = (): ScanAuthConfig | undefined => {
    if (authMode === "cookie") {
      return { strategy: "cookie", name: cookieName, value: cookieValue };
    }
    if (authMode === "form_login") {
      return {
        strategy: "form_login",
        login_url: loginUrl,
        username_field: usernameField,
        password_field: passwordField,
        username,
        password,
      };
    }
    return undefined;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const scan = await createScan.mutateAsync({ url, auth_config: buildAuthConfig() });
      setUrl("");
      setActiveScanId(scan.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("common.unexpected_error"));
    }
  };

  const disabled =
    createScan.isPending || liveStatus === "pending" || liveStatus === "running";

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2">
          <ScanLine className="h-4 w-4 text-primary" />
          {t("dashboard.scan_form_title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <p className="text-sm text-destructive rounded-lg bg-destructive/10 px-3 py-2 border border-destructive/20">
            {error}
          </p>
        )}
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex gap-2">
            <Input
              type="url"
              required
              placeholder="https://example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={disabled}
              className="flex-1 h-10"
            />
            <Button type="submit" disabled={disabled} size="lg" className="h-10 px-5">
              {createScan.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t("dashboard.scan_submitting")}
                </>
              ) : (
                t("dashboard.scan_submit")
              )}
            </Button>
          </div>

          <button
            type="button"
            onClick={() => setAuthOpen((v) => !v)}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
            aria-expanded={authOpen}
          >
            {authOpen ? "▾" : "▸"} {t("dashboard.auth_toggle")}
          </button>

          {authOpen && (
            <div className="space-y-3 rounded-lg border border-dashed p-4 bg-muted/30">
              <div className="flex gap-4 text-sm">
                {(["none", "cookie", "form_login"] as const).map((mode) => (
                  <label key={mode} className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="radio"
                      name="authMode"
                      checked={authMode === mode}
                      onChange={() => setAuthMode(mode)}
                    />
                    {mode === "none"
                      ? t("dashboard.auth_none")
                      : mode === "cookie"
                        ? t("dashboard.auth_cookie_label")
                        : t("dashboard.auth_form_label")}
                  </label>
                ))}
              </div>

              {authMode === "cookie" && (
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    type="text"
                    required
                    placeholder={t("dashboard.auth_cookie_name")}
                    value={cookieName}
                    onChange={(e) => setCookieName(e.target.value)}
                  />
                  <Input
                    type="text"
                    required
                    placeholder={t("dashboard.auth_cookie_value")}
                    value={cookieValue}
                    onChange={(e) => setCookieValue(e.target.value)}
                    className="font-mono"
                  />
                </div>
              )}

              {authMode === "form_login" && (
                <div className="space-y-2">
                  <Input
                    type="url"
                    required
                    placeholder={t("dashboard.auth_login_url")}
                    value={loginUrl}
                    onChange={(e) => setLoginUrl(e.target.value)}
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="text"
                      required
                      placeholder={t("dashboard.auth_username_field")}
                      value={usernameField}
                      onChange={(e) => setUsernameField(e.target.value)}
                      className="font-mono"
                    />
                    <Input
                      type="text"
                      required
                      placeholder={t("dashboard.auth_password_field")}
                      value={passwordField}
                      onChange={(e) => setPasswordField(e.target.value)}
                      className="font-mono"
                    />
                    <Input
                      type="text"
                      required
                      placeholder={t("dashboard.auth_username")}
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                    />
                    <Input
                      type="password"
                      required
                      placeholder={t("dashboard.auth_password")}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t("dashboard.auth_encrypted_hint")}
                  </p>
                </div>
              )}
            </div>
          )}
        </form>

        {activeScanId && liveStatus && liveStatus !== "completed" && (
          <ScanProgressBar status={liveStatus} />
        )}
        {liveStatus === "failed" && (
          <p className="text-sm text-destructive">{t("dashboard.scan_failed")}</p>
        )}
      </CardContent>
    </Card>
  );
}

// ── Scan result card ──────────────────────────────────────────────────────────

function ScanCard({ scan }: { scan: Scan }) {
  const [open, setOpen] = useState(false);
  const { t, i18n } = useTranslation();
  const locale = i18n.language === "fr" ? "fr-FR" : "en-US";

  const countBySeverity = scan.findings.reduce<Record<string, number>>((acc, f) => {
    acc[f.severity] = (acc[f.severity] ?? 0) + 1;
    return acc;
  }, {});

  const isPending = scan.status === "pending" || scan.status === "running";

  return (
    <Card className="overflow-hidden">
      <button
        onClick={() => !isPending && setOpen((v) => !v)}
        disabled={isPending}
        className="w-full text-left px-5 py-3.5 flex items-center justify-between hover:bg-muted/40 transition-colors disabled:cursor-default"
      >
        <div className="flex flex-col gap-0.5 min-w-0">
          <span className="text-sm font-medium truncate">{scan.url}</span>
          <span className="text-xs text-muted-foreground">
            {new Date(scan.created_at).toLocaleString(locale)}
          </span>
        </div>
        <div className="flex items-center gap-2 ml-4 shrink-0">
          {isPending ? (
            <span className="text-xs text-muted-foreground flex items-center gap-1.5">
              <Loader2 className="h-3 w-3 animate-spin" />
              {scan.status === "running" ? t("dashboard.scan_running") : t("dashboard.scan_pending")}
            </span>
          ) : scan.findings.length === 0 ? (
            <span className="text-xs text-emerald-600 font-medium dark:text-emerald-400">
              {t("dashboard.no_vulns")}
            </span>
          ) : (
            <>
              {(["critical", "high", "medium", "low", "info"] as const).map((sev) =>
                countBySeverity[sev] ? <SeverityBadge key={sev} severity={sev} /> : null
              )}
              <span className="text-xs text-muted-foreground">
                {scan.findings.length}{" "}
                {scan.findings.length > 1 ? t("dashboard.found_many") : t("dashboard.found_one")}
              </span>
            </>
          )}
          {!isPending && (
            <>
              <Link
                to={`/scans/${scan.id}`}
                onClick={(e) => e.stopPropagation()}
                className="text-xs text-primary hover:underline flex items-center gap-0.5"
              >
                <ExternalLink className="h-3 w-3" />
                {t("dashboard.report_link")}
              </Link>
              <span className="text-muted-foreground text-xs">{open ? "▲" : "▼"}</span>
            </>
          )}
        </div>
      </button>

      {open && scan.findings.length > 0 && (
        <div className="divide-y border-t">
          {scan.findings.map((f) => (
            <div key={f.id} className="px-5 py-3 space-y-1">
              <div className="flex items-center gap-2">
                <SeverityBadge severity={f.severity} />
                <span className="text-sm font-medium">{f.name}</span>
              </div>
              <p className="text-xs text-muted-foreground">{f.description}</p>
              {f.recommendation && (
                <p className="text-xs text-muted-foreground">
                  <span className="font-medium">{t("dashboard.recommendation")}</span>{" "}
                  {f.recommendation}
                </p>
              )}
              {f.evidence && (
                <p className="text-xs font-mono text-muted-foreground bg-muted px-2 py-1 rounded-md">
                  {f.evidence}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {open && scan.findings.length === 0 && (
        <p className="px-5 py-3 text-sm text-muted-foreground border-t">
          {t("dashboard.no_vulnerabilities")}
        </p>
      )}
    </Card>
  );
}

// ── History ───────────────────────────────────────────────────────────────────

function ScanHistory() {
  const { data: scans, isLoading } = useScanList();
  const { t } = useTranslation();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground text-sm py-8 justify-center">
        <Spinner size="sm" />
        {t("common.loading")}
      </div>
    );
  }

  if (!scans || scans.length === 0) {
    return (
      <EmptyState
        title={t("dashboard.no_scans_title")}
        description={t("dashboard.no_scans_desc")}
      />
    );
  }

  return (
    <div className="space-y-2">
      {scans.map((scan) => (
        <ScanCard key={scan.id} scan={scan} />
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function DashboardPage() {
  const { t } = useTranslation();

  return (
    <AppShell>
      <main className="container py-8 space-y-8 max-w-4xl">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("dashboard.title")}</h1>
          <p className="text-muted-foreground mt-1 text-sm">{t("dashboard.subtitle")}</p>
        </div>

        <ScanForm />

        <div className="space-y-3">
          <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
            {t("dashboard.scan_history")}
          </h2>
          <ScanHistory />
        </div>
      </main>
    </AppShell>
  );
}
