import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";

import { useLogin, useRegister } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";

export function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const register = useRegister();
  const login = useLogin();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await register.mutateAsync({ email, password, full_name: fullName || undefined });
      // Auto-login after successful registration
      await login.mutateAsync({ email, password });
      void navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erreur inattendue. Réessaie.");
    }
  };

  const isPending = register.isPending || login.isPending;

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="w-full max-w-md space-y-6">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-7 w-7 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight">WebGuard</h1>
        </div>

        <div className="rounded-lg border bg-card p-6 space-y-5">
          <h2 className="text-lg font-semibold">Créer un compte</h2>

          {error && (
            <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">
              {error}
            </p>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="fullName" className="text-sm font-medium">
                Nom complet <span className="text-muted-foreground">(optionnel)</span>
              </label>
              <input
                id="fullName"
                type="text"
                autoComplete="name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

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
                className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="password" className="text-sm font-medium">
                Mot de passe{" "}
                <span className="text-muted-foreground text-xs">(8 caractères minimum)</span>
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            <button
              type="submit"
              disabled={isPending}
              className="w-full rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {isPending ? "Création du compte…" : "Créer mon compte"}
            </button>
          </form>

          <p className="text-sm text-muted-foreground text-center">
            Déjà un compte ?{" "}
            <Link to="/login" className="font-medium underline underline-offset-4">
              Se connecter
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
