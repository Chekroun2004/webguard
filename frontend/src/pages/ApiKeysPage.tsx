import { useState } from "react";
import { AlertTriangle, Copy, Loader2, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { AppShell } from "@/components/AppShell";
import {
  useApiKeysList,
  useCreateApiKey,
  useRevokeApiKey,
  type ApiKey,
  type ApiKeyCreated,
} from "@/hooks/useApiKeys";
import { ApiError } from "@/lib/api";

// ── Modal shown ONCE after creation ──────────────────────────────────────────

function CreatedKeyModal({
  created,
  onClose,
}: {
  created: ApiKeyCreated;
  onClose: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const { t } = useTranslation();

  const copy = async () => {
    await navigator.clipboard.writeText(created.key);
    setCopied(true);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-card rounded-lg border max-w-lg w-full p-6 space-y-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h3 className="font-semibold">{t("api_keys.modal_title")}</h3>
            <p className="text-sm text-muted-foreground">{t("api_keys.modal_desc")}</p>
          </div>
        </div>

        <div className="rounded-md border bg-muted/40 p-3 break-all font-mono text-sm">
          {created.key}
        </div>

        <div className="flex gap-2 justify-end">
          <button
            onClick={copy}
            className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors flex items-center gap-1.5"
          >
            <Copy className="h-4 w-4" />
            {copied ? t("api_keys.modal_copied") : t("api_keys.modal_copy")}
          </button>
          <button
            onClick={onClose}
            className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:opacity-90 transition-opacity"
          >
            {t("api_keys.modal_confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Create form ──────────────────────────────────────────────────────────────

function CreateApiKeyForm({ onCreated }: { onCreated: (k: ApiKeyCreated) => void }) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const create = useCreateApiKey();
  const { t } = useTranslation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const created = await create.mutateAsync(name);
      setName("");
      onCreated(created);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("common.unexpected_error"));
    }
  };

  return (
    <div className="rounded-lg border bg-card p-6 space-y-4">
      <h2 className="font-semibold">{t("api_keys.create_title")}</h2>
      {error && (
        <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">
          {error}
        </p>
      )}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          required
          minLength={1}
          maxLength={128}
          placeholder={t("api_keys.name_placeholder")}
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={create.isPending}
          className="flex-1 rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={create.isPending}
          className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center gap-1.5"
        >
          {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          {t("api_keys.create_btn")}
        </button>
      </form>
    </div>
  );
}

// ── Key row ──────────────────────────────────────────────────────────────────

function ApiKeyRow({ apiKey }: { apiKey: ApiKey }) {
  const revoke = useRevokeApiKey();
  const isRevoked = apiKey.revoked_at !== null;
  const { t, i18n } = useTranslation();
  const locale = i18n.language === "fr" ? "fr-FR" : "en-US";

  return (
    <div className="rounded-lg border bg-card px-4 py-3 flex items-center justify-between gap-4">
      <div className="min-w-0 space-y-0.5">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm truncate">{apiKey.name}</span>
          <code className="text-xs rounded bg-muted px-1.5 py-0.5 font-mono">
            {apiKey.prefix}…
          </code>
          {isRevoked ? (
            <span className="text-xs rounded bg-destructive/10 text-destructive px-1.5 py-0.5">
              {t("api_keys.revoked")}
            </span>
          ) : (
            <span className="text-xs rounded bg-green-500/15 text-green-600 px-1.5 py-0.5">
              {t("api_keys.active")}
            </span>
          )}
        </div>
        <div className="text-xs text-muted-foreground">
          {t("api_keys.created_at", { date: new Date(apiKey.created_at).toLocaleString(locale) })}
          {apiKey.last_used_at && (
            <>
              {" • "}{t("api_keys.used_at", { date: new Date(apiKey.last_used_at).toLocaleString(locale) })}
            </>
          )}
        </div>
      </div>
      {!isRevoked && (
        <button
          onClick={() => revoke.mutate(apiKey.id)}
          disabled={revoke.isPending}
          className="text-xs rounded-md border px-2 py-1 hover:bg-destructive/10 hover:text-destructive disabled:opacity-50 flex items-center gap-1"
          aria-label={t("api_keys.revoke_btn")}
        >
          <Trash2 className="h-3 w-3" />
          {t("api_keys.revoke_btn")}
        </button>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export function ApiKeysPage() {
  const { data: keys, isLoading } = useApiKeysList();
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);
  const { t } = useTranslation();

  return (
    <AppShell>
      <main className="container py-8 space-y-8 max-w-2xl">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("api_keys.title")}</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            {t("api_keys.subtitle")}{" "}
            <code className="text-xs bg-muted px-1.5 py-0.5 rounded">X-API-Key: wgk_xxx</code>{" "}
            {t("api_keys.subtitle_hint")}
          </p>
        </div>

        <CreateApiKeyForm onCreated={setCreated} />

        <div className="space-y-3">
          <h2 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">
            {t("api_keys.list_title")}
          </h2>
          {isLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> {t("common.loading")}
            </div>
          ) : !keys || keys.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t("api_keys.empty")}</p>
          ) : (
            <div className="space-y-2">
              {keys.map((k) => (
                <ApiKeyRow key={k.id} apiKey={k} />
              ))}
            </div>
          )}
        </div>
      </main>

      {created && <CreatedKeyModal created={created} onClose={() => setCreated(null)} />}
    </AppShell>
  );
}
