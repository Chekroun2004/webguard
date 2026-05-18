import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Clock, Loader2, ShieldCheck } from "lucide-react";

import { useDomainList, useRegisterDomain, useVerifyDomain, type VerificationMethod } from "@/hooks/useDomains";
import { ApiError } from "@/lib/api";
import type { Domain } from "@/hooks/useDomains";

// ── Add domain form ───────────────────────────────────────────────────────────

function AddDomainForm() {
  const [domain, setDomain] = useState("");
  const [method, setMethod] = useState<VerificationMethod>("file");
  const [error, setError] = useState<string | null>(null);

  const register = useRegisterDomain();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await register.mutateAsync({ domain, method });
      setDomain("");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erreur inattendue.");
    }
  };

  return (
    <div className="rounded-lg border bg-card p-6 space-y-4">
      <h2 className="font-semibold">Ajouter un domaine</h2>
      {error && (
        <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">{error}</p>
      )}
      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          type="text"
          required
          placeholder="example.com"
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          disabled={register.isPending}
          className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
        />
        <div className="flex gap-4 text-sm">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="radio"
              value="file"
              checked={method === "file"}
              onChange={() => setMethod("file")}
            />
            Fichier de vérification
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="radio"
              value="dns"
              checked={method === "dns"}
              onChange={() => setMethod("dns")}
            />
            Enregistrement DNS TXT
          </label>
        </div>
        <button
          type="submit"
          disabled={register.isPending}
          className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center gap-1.5"
        >
          {register.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Ajouter
        </button>
      </form>
    </div>
  );
}

// ── Domain card ───────────────────────────────────────────────────────────────

function DomainCard({ domain }: { domain: Domain }) {
  const [error, setError] = useState<string | null>(null);
  const verify = useVerifyDomain();

  const handleVerify = async () => {
    setError(null);
    try {
      await verify.mutateAsync(domain.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Vérification échouée.");
    }
  };

  const isFile = domain.verification_method === "file";
  const instruction = isFile
    ? `Créez le fichier https://${domain.domain}/webguard-verify-${domain.verification_token}.txt contenant uniquement le token ci-dessous.`
    : `Ajoutez un enregistrement DNS TXT sur _webguard.${domain.domain} avec la valeur : webguard-verify=${domain.verification_token}`;

  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      <div className="px-4 py-3 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 min-w-0">
          {domain.is_verified ? (
            <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
          ) : (
            <Clock className="h-4 w-4 text-muted-foreground shrink-0" />
          )}
          <span className="font-medium text-sm truncate">{domain.domain}</span>
          <span className="text-xs text-muted-foreground shrink-0">
            ({domain.verification_method === "file" ? "Fichier" : "DNS"})
          </span>
        </div>
        {domain.is_verified ? (
          <span className="text-xs text-green-600 font-medium shrink-0">Vérifié ✓</span>
        ) : (
          <button
            onClick={handleVerify}
            disabled={verify.isPending}
            className="shrink-0 rounded-md bg-primary text-primary-foreground px-3 py-1 text-xs font-medium hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center gap-1"
          >
            {verify.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
            Vérifier
          </button>
        )}
      </div>

      {!domain.is_verified && (
        <div className="border-t px-4 py-3 space-y-2 bg-muted/30">
          <p className="text-xs text-muted-foreground">{instruction}</p>
          <div className="rounded bg-muted px-2 py-1 font-mono text-xs break-all">
            {domain.verification_token}
          </div>
          {error && (
            <p className="text-xs text-destructive">{error}</p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function DomainsPage() {
  const { data: domains, isLoading } = useDomainList();

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container flex h-14 items-center gap-4">
          <ShieldCheck className="h-5 w-5 text-primary" />
          <span className="font-semibold"><span className="text-[#6366f1]">Web</span>Guard</span>
          <span className="text-muted-foreground">/</span>
          <span className="text-sm">Mes domaines</span>
        </div>
      </header>

      <main className="container py-10 space-y-8 max-w-2xl">
        <div className="flex items-center gap-3">
          <Link
            to="/dashboard"
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Tableau de bord
          </Link>
        </div>

        <div>
          <h1 className="text-2xl font-bold">Vérification de domaines</h1>
          <p className="text-muted-foreground mt-1">
            Prouvez que vous contrôlez un domaine avant de le scanner.
          </p>
        </div>

        <AddDomainForm />

        <div className="space-y-3">
          <h2 className="font-semibold">Domaines enregistrés</h2>
          {isLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="h-4 w-4 animate-spin" /> Chargement…
            </div>
          ) : !domains || domains.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Aucun domaine enregistré. Ajoutez-en un ci-dessus.
            </p>
          ) : (
            <div className="space-y-2">
              {domains.map((d) => (
                <DomainCard key={d.id} domain={d} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
