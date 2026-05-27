import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, Loader2, LogOut, ShieldCheck } from "lucide-react";

import { useCurrentUser, useLogout } from "@/hooks/useAuth";
import { useCreateScan, useScanList, type ScanAuthConfig } from "@/hooks/useScan";
import { useScanEvents } from "@/hooks/useScanEvents";
import { SeverityBadge } from "@/components/SeverityBadge";
import { ScanProgressBar } from "@/components/ScanProgressBar";
import { ThemeToggle } from "@/components/ThemeToggle";
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
      setError(err instanceof ApiError ? err.detail : "Erreur inattendue.");
    }
  };

  const disabled =
    createScan.isPending || liveStatus === "pending" || liveStatus === "running";

  return (
    <div className="rounded-lg border bg-card p-6 space-y-4">
      <h2 className="font-semibold">Lancer un scan</h2>
      {error && (
        <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">{error}</p>
      )}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex gap-2">
          <input
            type="url"
            required
            placeholder="https://example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={disabled}
            className="flex-1 rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={disabled}
            className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center gap-1.5"
          >
            {createScan.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Envoi…
              </>
            ) : (
              "Scanner"
            )}
          </button>
        </div>

        <button
          type="button"
          onClick={() => setAuthOpen((v) => !v)}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          aria-expanded={authOpen}
        >
          {authOpen ? "▾" : "▸"} Authentification (optionnel)
        </button>

        {authOpen && (
          <div className="space-y-3 rounded-md border border-dashed p-3 bg-muted/30">
            <div className="flex gap-3 text-sm">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="authMode"
                  checked={authMode === "none"}
                  onChange={() => setAuthMode("none")}
                />
                Aucune
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="authMode"
                  checked={authMode === "cookie"}
                  onChange={() => setAuthMode("cookie")}
                />
                Cookie de session
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="authMode"
                  checked={authMode === "form_login"}
                  onChange={() => setAuthMode("form_login")}
                />
                Login form
              </label>
            </div>

            {authMode === "cookie" && (
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  required
                  placeholder="Nom (ex: session)"
                  value={cookieName}
                  onChange={(e) => setCookieName(e.target.value)}
                  className="rounded-md border bg-background px-3 py-2 text-sm"
                />
                <input
                  type="text"
                  required
                  placeholder="Valeur"
                  value={cookieValue}
                  onChange={(e) => setCookieValue(e.target.value)}
                  className="rounded-md border bg-background px-3 py-2 text-sm font-mono"
                />
              </div>
            )}

            {authMode === "form_login" && (
              <div className="space-y-2">
                <input
                  type="url"
                  required
                  placeholder="URL du login (ex: https://example.com/login)"
                  value={loginUrl}
                  onChange={(e) => setLoginUrl(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    required
                    placeholder="Nom du champ user"
                    value={usernameField}
                    onChange={(e) => setUsernameField(e.target.value)}
                    className="rounded-md border bg-background px-3 py-2 text-sm font-mono"
                  />
                  <input
                    type="text"
                    required
                    placeholder="Nom du champ password"
                    value={passwordField}
                    onChange={(e) => setPasswordField(e.target.value)}
                    className="rounded-md border bg-background px-3 py-2 text-sm font-mono"
                  />
                  <input
                    type="text"
                    required
                    placeholder="Identifiant"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="rounded-md border bg-background px-3 py-2 text-sm"
                  />
                  <input
                    type="password"
                    required
                    placeholder="Mot de passe"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="rounded-md border bg-background px-3 py-2 text-sm"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Les identifiants sont chiffrés (Fernet) avant d'être stockés.
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
        <p className="text-sm text-destructive">Le scan a échoué. Réessaie.</p>
      )}
    </div>
  );
}

// ── Scan result card ──────────────────────────────────────────────────────────

function ScanCard({ scan }: { scan: Scan }) {
  const [open, setOpen] = useState(false);
  const countBySeverity = scan.findings.reduce<Record<string, number>>((acc, f) => {
    acc[f.severity] = (acc[f.severity] ?? 0) + 1;
    return acc;
  }, {});

  const isPending = scan.status === "pending" || scan.status === "running";

  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      <button
        onClick={() => !isPending && setOpen((v) => !v)}
        disabled={isPending}
        className="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-muted/40 transition-colors disabled:cursor-default"
      >
        <div className="flex flex-col gap-0.5 min-w-0">
          <span className="text-sm font-medium truncate">{scan.url}</span>
          <span className="text-xs text-muted-foreground">
            {new Date(scan.created_at).toLocaleString("fr-FR")}
          </span>
        </div>
        <div className="flex items-center gap-2 ml-4 shrink-0">
          {isPending ? (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" />
              {scan.status === "running" ? "Scan en cours…" : "En attente…"}
            </span>
          ) : scan.findings.length === 0 ? (
            <span className="text-xs text-green-600 font-medium">✓ Aucune vulnérabilité</span>
          ) : (
            <>
              {(["critical", "high", "medium", "low", "info"] as const).map((sev) =>
                countBySeverity[sev] ? (
                  <SeverityBadge key={sev} severity={sev} />
                ) : null
              )}
              <span className="text-xs text-muted-foreground">
                {scan.findings.length} trouvé{scan.findings.length > 1 ? "es" : "e"}
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
                Rapport
              </Link>
              <span className="text-muted-foreground text-xs">{open ? "▲" : "▼"}</span>
            </>
          )}
        </div>
      </button>

      {open && scan.findings.length > 0 && (
        <div className="divide-y border-t">
          {scan.findings.map((f) => (
            <div key={f.id} className="px-4 py-3 space-y-1">
              <div className="flex items-center gap-2">
                <SeverityBadge severity={f.severity} />
                <span className="text-sm font-medium">{f.name}</span>
              </div>
              <p className="text-xs text-muted-foreground">{f.description}</p>
              {f.recommendation && (
                <p className="text-xs text-muted-foreground">
                  <span className="font-medium">Recommandation :</span> {f.recommendation}
                </p>
              )}
              {f.evidence && (
                <p className="text-xs font-mono text-muted-foreground bg-muted px-2 py-1 rounded">
                  {f.evidence}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {open && scan.findings.length === 0 && (
        <p className="px-4 py-3 text-sm text-muted-foreground border-t">
          Aucune vulnérabilité détectée — site bien configuré 🎉
        </p>
      )}
    </div>
  );
}

// ── History ───────────────────────────────────────────────────────────────────

function ScanHistory() {
  const { data: scans, isLoading } = useScanList();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground text-sm">
        <Loader2 className="h-4 w-4 animate-spin" /> Chargement…
      </div>
    );
  }

  if (!scans || scans.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Aucun scan effectué. Lancez votre premier scan ci-dessus.
      </p>
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
  const { data: user } = useCurrentUser();
  const logout = useLogout();

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container flex h-14 items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <span className="font-semibold"><span className="text-[#6366f1]">Web</span>Guard</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground hidden sm:block">{user?.email}</span>
            <Link
              to="/diff"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Comparer
            </Link>
            <Link
              to="/domains"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Mes domaines
            </Link>
            <Link
              to="/scheduled"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Scans planifiés
            </Link>
            <Link
              to="/webhooks"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Webhooks
            </Link>
            <Link
              to="/security"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Sécurité
            </Link>
            <ThemeToggle />
            <button
              onClick={logout}
              className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Déconnexion
            </button>
          </div>
        </div>
      </header>

      <main className="container py-10 space-y-8">
        <div>
          <h1 className="text-2xl font-bold">
            Bonjour, {user?.full_name ?? user?.email} 👋
          </h1>
          <p className="text-muted-foreground mt-1">
            Scannez un site pour détecter les en-têtes de sécurité manquants.
          </p>
        </div>

        <ScanForm />

        <div className="space-y-3">
          <h2 className="font-semibold">Historique des scans</h2>
          <ScanHistory />
        </div>
      </main>
    </div>
  );
}
