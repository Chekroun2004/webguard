import { LogOut, ShieldCheck } from "lucide-react";

import { useCurrentUser, useLogout } from "@/hooks/useAuth";

export function DashboardPage() {
  const { data: user } = useCurrentUser();
  const logout = useLogout();

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container flex h-14 items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <span className="font-semibold">WebGuard</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground hidden sm:block">{user?.email}</span>
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

      <main className="container py-10 space-y-6">
        <div>
          <h1 className="text-2xl font-bold">
            Bonjour, {user?.full_name ?? user?.email} 👋
          </h1>
          <p className="text-muted-foreground mt-1">
            Bienvenue sur WebGuard. Le scanner sera disponible à l'Étape 3.
          </p>
        </div>

        <div className="rounded-lg border bg-card p-6 max-w-sm">
          <p className="text-sm font-medium text-muted-foreground mb-3">Votre profil</p>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Email</dt>
              <dd className="font-mono">{user?.email}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Rôle</dt>
              <dd>{user?.role}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Compte actif</dt>
              <dd>{user?.is_active ? "Oui" : "Non"}</dd>
            </div>
          </dl>
        </div>
      </main>
    </div>
  );
}
