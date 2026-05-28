import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldAlert } from "lucide-react";

import { useLogin, useRegister } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

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
      await login.mutateAsync({ email, password });
      void navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erreur inattendue. Réessaie.");
    }
  };

  const isPending = register.isPending || login.isPending;

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left panel — brand */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-brand flex-col justify-between p-12 text-white">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
            <ShieldAlert className="h-5 w-5 text-white" />
          </div>
          <span className="font-bold text-xl tracking-tight">WebGuard</span>
        </div>

        <div className="space-y-4">
          <h2 className="text-3xl font-bold leading-tight">
            Un compte gratuit. Une visibilité totale sur votre sécurité web.
          </h2>
          <p className="text-white/70 text-sm leading-relaxed">
            Scans à la demande, rapports PDF exportables, comparaison de scans, alertes webhook
            Slack/Discord et bien plus. Prêt en 30 secondes.
          </p>
        </div>

        <p className="text-white/40 text-xs">WebGuard — Portfolio Master IGOV · FSR-UM5 Rabat</p>
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
              <CardTitle>Créer un compte</CardTitle>
              <CardDescription>Rejoignez WebGuard et commencez à scanner gratuitement.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {error && (
                <p className="text-sm text-destructive rounded-lg bg-destructive/10 px-3 py-2 border border-destructive/20">
                  {error}
                </p>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label htmlFor="fullName" className="text-sm font-medium">
                    Nom complet{" "}
                    <span className="text-muted-foreground font-normal">(optionnel)</span>
                  </label>
                  <Input
                    id="fullName"
                    type="text"
                    autoComplete="name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                </div>

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
                    Mot de passe{" "}
                    <span className="text-muted-foreground font-normal text-xs">
                      (8 caractères minimum)
                    </span>
                  </label>
                  <Input
                    id="password"
                    type="password"
                    required
                    minLength={8}
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>

                <Button type="submit" disabled={isPending} className="w-full" size="lg">
                  {isPending ? "Création du compte…" : "Créer mon compte"}
                </Button>
              </form>

              <p className="text-sm text-muted-foreground text-center">
                Déjà un compte ?{" "}
                <Link
                  to="/login"
                  className="font-medium text-primary hover:underline underline-offset-4"
                >
                  Se connecter
                </Link>
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
