import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldAlert } from "lucide-react";

import { useLogin, useLoginTotp } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

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
    <div className="min-h-screen bg-background flex">
      {/* Left panel — animated mesh background */}
      <div
        className="hidden lg:flex lg:w-1/2 relative overflow-hidden flex-col justify-between p-12 text-white border-r border-white/[0.06]"
        style={{ background: "hsl(240 20% 4%)" }}
      >
        {/* Animated glow orbs */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="animate-mesh-1 absolute -top-32 -left-32 h-[500px] w-[500px] rounded-full bg-indigo-600/25 blur-[100px]" />
          <div className="animate-mesh-2 absolute -bottom-32 right-0 h-[400px] w-[400px] rounded-full bg-violet-600/20 blur-[80px]" />
          <div className="animate-mesh-3 absolute top-1/2 left-1/3 h-[300px] w-[300px] rounded-full bg-indigo-500/10 blur-[60px]" />
        </div>

        <div className="relative z-10 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 flex items-center justify-center">
            <ShieldAlert className="h-5 w-5 text-white" />
          </div>
          <span className="font-display font-bold text-xl tracking-tight">WebGuard</span>
        </div>

        <div className="relative z-10 space-y-5">
          <h2 className="font-display text-4xl font-bold leading-tight">
            Détectez les failles avant que les attaquants ne le fassent.
          </h2>
          <p className="text-white/60 text-sm leading-relaxed max-w-sm">
            13 scanners actifs et passifs. Rapports PDF. Scans planifiés. Webhooks Slack/Discord.
            Authentification à deux facteurs. Tout ce qu'il faut pour sécuriser votre surface
            d'attaque web.
          </p>
          <div className="flex gap-6 pt-2">
            <div>
              <p className="text-2xl font-display font-bold">13</p>
              <p className="text-white/50 text-xs mt-0.5">Scanners</p>
            </div>
            <div className="w-px bg-white/10" />
            <div>
              <p className="text-2xl font-display font-bold">PDF</p>
              <p className="text-white/50 text-xs mt-0.5">Rapports</p>
            </div>
            <div className="w-px bg-white/10" />
            <div>
              <p className="text-2xl font-display font-bold">2FA</p>
              <p className="text-white/50 text-xs mt-0.5">Sécurisé</p>
            </div>
          </div>
        </div>

        <p className="relative z-10 text-white/30 text-xs">
          WebGuard — Portfolio Master IGOV · FSR-UM5 Rabat
        </p>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md space-y-6">
          {/* Mobile brand */}
          <div className="flex items-center gap-2 lg:hidden">
            <div className="w-7 h-7 rounded-lg bg-gradient-brand flex items-center justify-center">
              <span className="text-white text-xs font-bold">W</span>
            </div>
            <span className="font-bold text-lg">
              <span className="text-[#6366f1]">Web</span>Guard
            </span>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>{pendingToken ? "Vérification 2FA" : "Connexion"}</CardTitle>
              <CardDescription>
                {pendingToken
                  ? "Entrez le code de votre application TOTP."
                  : "Entrez vos identifiants pour accéder à votre espace."}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {error && (
                <p className="text-sm text-destructive rounded-lg bg-destructive/10 px-3 py-2 border border-destructive/20">
                  {error}
                </p>
              )}

              {!pendingToken ? (
                <form onSubmit={handleCredentialsSubmit} className="space-y-4">
                  <div className="space-y-1.5">
                    <label htmlFor="email" className="text-sm font-medium">
                      Email
                    </label>
                    <Input
                      id="email"
                      type="email"
                      required
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label htmlFor="password" className="text-sm font-medium">
                      Mot de passe
                    </label>
                    <Input
                      id="password"
                      type="password"
                      required
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>
                  <Button type="submit" disabled={login.isPending} className="w-full" size="lg">
                    {login.isPending ? "Connexion…" : "Se connecter"}
                  </Button>
                </form>
              ) : (
                <form onSubmit={handleTotpSubmit} className="space-y-4">
                  <Input
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
                    className="font-mono text-center tracking-[0.5em] text-lg h-12"
                  />
                  <Button
                    type="submit"
                    disabled={totpCode.length !== 6 || loginTotp.isPending}
                    className="w-full"
                    size="lg"
                  >
                    {loginTotp.isPending ? "Vérification…" : "Valider"}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="w-full text-muted-foreground"
                    onClick={() => {
                      setPendingToken(null);
                      setTotpCode("");
                      setError(null);
                    }}
                  >
                    ← Recommencer
                  </Button>
                </form>
              )}

              {!pendingToken && (
                <p className="text-sm text-muted-foreground text-center">
                  Pas encore de compte ?{" "}
                  <Link
                    to="/register"
                    className="font-medium text-primary hover:underline underline-offset-4"
                  >
                    S'inscrire
                  </Link>
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
