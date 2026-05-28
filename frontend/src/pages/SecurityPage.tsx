import { useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();

  const startEnrollment = async () => {
    setError(null);
    try {
      const data = await enroll.mutateAsync();
      setEnrollment(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("common.unexpected_error"));
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
      setError(err instanceof ApiError ? err.detail : t("security.totp_invalid"));
    }
  };

  if (!enrollment) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">{t("security.totp_enable_desc")}</p>
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
          {t("security.totp_enable_btn")}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">{t("security.totp_scan_desc")}</p>
      <div className="rounded-md border bg-white p-4 inline-block">
        <QRCodeSVG value={enrollment.otpauth_uri} size={180} level="M" />
      </div>
      <details className="text-xs text-muted-foreground">
        <summary className="cursor-pointer">{t("security.totp_manual")}</summary>
        <code className="mt-1 block break-all bg-muted px-2 py-1 rounded">
          {enrollment.secret}
        </code>
      </details>

      {error && (
        <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">{error}</p>
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
          {t("security.totp_confirm_btn")}
        </button>
      </form>
    </div>
  );
}

function DisableFlow() {
  const disable = useTotpDisable();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { t } = useTranslation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await disable.mutateAsync(code);
      setCode("");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("security.totp_invalid"));
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm">
        <CheckCircle2 className="h-4 w-4 text-green-600" />
        <span>{t("security.totp_enabled_status")}</span>
      </div>
      <p className="text-sm text-muted-foreground">{t("security.totp_disable_desc")}</p>
      {error && (
        <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">{error}</p>
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
          {t("security.totp_disable_btn")}
        </button>
      </form>
    </div>
  );
}

export function SecurityPage() {
  const { data: status, isLoading, refetch } = useTotpStatus();
  const { t } = useTranslation();

  return (
    <AppShell>
      <main className="container py-8 space-y-8 max-w-2xl">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("security.title")}</h1>
          <p className="text-muted-foreground mt-1 text-sm">{t("security.subtitle")}</p>
        </div>

        <div className="rounded-lg border bg-card p-6 space-y-4">
          <h2 className="font-semibold">{t("security.totp_section")}</h2>
          {isLoading || !status ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> {t("common.loading")}
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
