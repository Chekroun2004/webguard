import { useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";

type HealthResponse = { status: string; environment: string };

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function App() {
  const { data, isLoading, isError } = useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/health`);
      if (!res.ok) throw new Error(`Backend status ${res.status}`);
      return (await res.json()) as HealthResponse;
    },
  });

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center p-6">
      <main className="max-w-xl w-full space-y-8">
        <header className="space-y-3">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-9 w-9 text-primary" />
            <h1 className="text-4xl font-bold tracking-tight">WebGuard</h1>
          </div>
          <p className="text-muted-foreground">
            Scanner de vulnérabilités web — étape&nbsp;1&nbsp;: bootstrap de la plateforme.
          </p>
        </header>

        <section className="rounded-lg border bg-card p-5 space-y-2">
          <h2 className="text-sm font-medium text-muted-foreground">État du backend</h2>
          {isLoading && <p className="text-sm">Connexion en cours…</p>}
          {isError && (
            <p className="text-destructive text-sm">
              Impossible de joindre l'API ({API_BASE}). Vérifie que le backend tourne.
            </p>
          )}
          {data && (
            <p className="flex items-center gap-2">
              <span className="font-mono text-sm rounded bg-muted px-2 py-1">{data.status}</span>
              <span className="text-muted-foreground text-sm">env: {data.environment}</span>
            </p>
          )}
        </section>

        <footer className="text-xs text-muted-foreground">
          API: <code className="font-mono">{API_BASE}</code>
        </footer>
      </main>
    </div>
  );
}

export default App;
