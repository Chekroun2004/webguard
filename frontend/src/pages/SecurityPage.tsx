import { useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";

import { AppShell } from "@/components/AppShell";
import {
  useTotpConfirm,
  useTotpDisable,
  useTotpEnroll,
  useTotpStatus,
  type TotpEnrollResponse,
} from "@/hooks/useTotp";
import { ApiError } from "@/lib/api";

function EnableFlow({ onConfirmed }: { onConfirmed: () => void }) {
  const enroll = useTotpEnroll();
  const confirm = useTotpConfirm();
  const [enrollment, setEnrollment] = useState<TotpEnrollResponse | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  const startEnrollment = async () => {
    setError(null);
    try {
      const data = await enroll.mutateAsync();
      setEnrollment(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erreur inattendue.");
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await confirm.mutateAsync(code);
      setCode("");
      setEnrollment(null);
      onConfirmed();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Code invalide.");
    }
  };

  if (!enrollment) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Activez l'authentification à deux facteurs pour ajouter une étape de vérification
          (Google Authenticator, 1Password…) à votre connexion.
        </p>
        {error && (
          <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">
            {error}
          </p>
        )}
        <button
          onClick={startEnrollment}
          disabled={enroll.isPending}
          className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center gap-1.5"
        >
          {enroll.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Activer la 2FA
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Scannez ce QR code avec votre application TOTP, puis saisissez le code à 6 chiffres
        affiché.
      </p>
      <div className="rounded-md border bg-white p-4 inline-block">
        <QRCodeSVG value={enrollment.otpauth_uri} size={180} level="M" />
      </div>
      <details className="text-xs text-muted-foreground">
        <summary className="cursor-pointer">Saisir manuellement la clé</summary>
        <code className="mt-1 block break-all bg-muted px-2 py-1 rounded">
          {enrollment.secret}
        </code>
      </details>

      {error && (
        <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">
          {error}
        </p>
      )}
      <form onSubmit={handleConfirm} className="flex gap-2 items-center">
        <input
          type="text"
          inputMode="numeric"
          pattern="[0-9]{6}"
          maxLength={6}
          required
          placeholder="123456"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          disabled={confirm.isPending}
          className="w-32 rounded-md border bg-background px-3 py-2 text-sm font-mono tracking-widest text-center"
        />
        <button
          type="submit"
          disabled={code.length !== 6 || confirm.isPending}
          className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center gap-1.5"
        >
          {confirm.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Confirmer
        </button>
      </form>
    </div>
  );
}

function DisableFlow() {
  const disable = useTotpDisable();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await disable.mutateAsync(code);
      setCode("");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Code invalide.");
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm">
        <CheckCircle2 className="h-4 w-4 text-green-600" />
        <span>2FA activée sur votre compte.</span>
      </div>
      <p className="text-sm text-muted-foreground">
        Pour désactiver, confirmez avec un code valide.
      </p>
      {error && (
        <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">
          {error}
        </p>
      )}
      <form onSubmit={handleSubmit} className="flex gap-2 items-center">
        <input
          type="text"
          inputMode="numeric"
          pattern="[0-9]{6}"
          maxLength={6}
          required
          placeholder="123456"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          disabled={disable.isPending}
          className="w-32 rounded-md border bg-background px-3 py-2 text-sm font-mono tracking-widest text-center"
        />
        <button
          type="submit"
          disabled={code.length !== 6 || disable.isPending}
          className="rounded-md border border-destructive text-destructive px-4 py-2 text-sm font-medium hover:bg-destructive/10 disabled:opacity-50 transition-colors flex items-center gap-1.5"
        >
          {disable.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Désactiver
        </button>
      </form>
    </div>
  );
}

export function SecurityPage() {
  const { data: status, isLoading, refetch } = useTotpStatus();

  return (
    <AppShell>
      <main className="container py-8 space-y-8 max-w-2xl">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Sécurité du compte</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Renforcez la connexion à votre compte WebGuard.
          </p>
        </div>

        <div className="rounded-lg border bg-card p-6 space-y-4">
          <h2 className="font-semibold">Authentification à deux facteurs (TOTP)</h2>
          {isLoading || !status ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Chargement…
            </div>
          ) : status.enabled ? (
            <DisableFlow />
          ) : (
            <EnableFlow onConfirmed={() => void refetch()} />
          )}
        </div>
      </main>
    </AppShell>
  );
}
