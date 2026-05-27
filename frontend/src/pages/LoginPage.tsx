import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";

import { useLogin, useLoginTotp } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pendingToken, setPendingToken] = useState<string | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  const login = useLogin();
  const loginTotp = useLoginTotp();
  const navigate = useNavigate();

  const handleCredentialsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const resp = await login.mutateAsync({ email, password });
      if (resp.totp_required && resp.pending_token) {
        setPendingToken(resp.pending_token);
        return;
      }
      void navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erreur inattendue. Réessaie.");
    }
  };

  const handleTotpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pendingToken) return;
    setError(null);
    try {
      await loginTotp.mutateAsync({ pending_token: pendingToken, code: totpCode });
      void navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Code 2FA invalide.");
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="w-full max-w-md space-y-6">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-7 w-7 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight">
            <span className="text-[#6366f1]">Web</span>Guard
          </h1>
        </div>

        <div className="rounded-lg border bg-card p-6 space-y-5">
          <h2 className="text-lg font-semibold">
            {pendingToken ? "Vérification 2FA" : "Connexion"}
          </h2>

          {error && (
            <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">
              {error}
            </p>
          )}

          {!pendingToken ? (
            <form onSubmit={handleCredentialsSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="email" className="text-sm font-medium">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="password" className="text-sm font-medium">
                  Mot de passe
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
                />
              </div>

              <button
                type="submit"
                disabled={login.isPending}
                className="w-full rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
              >
                {login.isPending ? "Connexion…" : "Se connecter"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleTotpSubmit} className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Entrez le code à 6 chiffres affiché par votre application TOTP.
              </p>
              <input
                id="totp"
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                required
                autoFocus
                placeholder="123456"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm font-mono text-center tracking-widest focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={totpCode.length !== 6 || loginTotp.isPending}
                className="w-full rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
              >
                {loginTotp.isPending ? "Vérification…" : "Valider"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setPendingToken(null);
                  setTotpCode("");
                  setError(null);
                }}
                className="w-full text-xs text-muted-foreground hover:text-foreground"
              >
                ← Recommencer
              </button>
            </form>
          )}

          {!pendingToken && (
            <p className="text-sm text-muted-foreground text-center">
              Pas encore de compte ?{" "}
              <Link to="/register" className="font-medium underline underline-offset-4">
                S'inscrire
              </Link>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
