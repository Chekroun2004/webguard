import { useState } from "react";
import { CheckCircle2, Loader2, Trash2, XCircle } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import {
  useCreateWebhook,
  useDeleteWebhook,
  useTestWebhook,
  useUpdateWebhook,
  useWebhooksList,
  type Webhook,
  type WebhookProvider,
} from "@/hooks/useWebhooks";
import { ApiError } from "@/lib/api";

// ── Add webhook form ─────────────────────────────────────────────────────────

function AddWebhookForm() {
  const [url, setUrl] = useState("");
  const [provider, setProvider] = useState<WebhookProvider>("slack");
  const [error, setError] = useState<string | null>(null);

  const create = useCreateWebhook();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await create.mutateAsync({ url, provider });
      setUrl("");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Erreur inattendue.");
    }
  };

  return (
    <div className="rounded-lg border bg-card p-6 space-y-4">
      <h2 className="font-semibold">Ajouter un webhook</h2>
      {error && (
        <p className="text-sm text-destructive rounded-md bg-destructive/10 px-3 py-2">{error}</p>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <label className="block text-sm font-medium">Provider</label>
          <div className="flex gap-3 text-sm">
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="radio"
                name="provider"
                checked={provider === "slack"}
                onChange={() => setProvider("slack")}
              />
              Slack
            </label>
            <label className="flex items-center gap-1.5 cursor-pointer">
              <input
                type="radio"
                name="provider"
                checked={provider === "discord"}
                onChange={() => setProvider("discord")}
              />
              Discord
            </label>
          </div>
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium">URL du webhook</label>
          <input
            type="url"
            required
            placeholder={
              provider === "slack"
                ? "https://hooks.slack.com/services/T000/B000/xxx"
                : "https://discord.com/api/webhooks/123/abc"
            }
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={create.isPending}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
          />
        </div>

        <button
          type="submit"
          disabled={create.isPending}
          className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center gap-1.5"
        >
          {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Ajouter
        </button>
      </form>
    </div>
  );
}

// ── Webhook card ─────────────────────────────────────────────────────────────

function WebhookCard({ webhook }: { webhook: Webhook }) {
  const toggle = useUpdateWebhook();
  const del = useDeleteWebhook();
  const test = useTestWebhook();
  const [lastTest, setLastTest] = useState<null | { delivered: boolean }>(null);

  const onTest = async () => {
    setLastTest(null);
    try {
      const result = await test.mutateAsync(webhook.id);
      setLastTest(result);
    } catch {
      setLastTest({ delivered: false });
    }
  };

  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      <div className="px-4 py-3 flex items-center justify-between gap-4">
        <div className="min-w-0 space-y-0.5">
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-wide rounded bg-muted px-1.5 py-0.5">
              {webhook.provider}
            </span>
            <span className="font-mono text-xs truncate max-w-xs">{webhook.url}</span>
            {webhook.is_active ? (
              <span className="text-xs rounded bg-green-500/15 text-green-600 px-1.5 py-0.5">
                actif
              </span>
            ) : (
              <span className="text-xs rounded bg-muted text-muted-foreground px-1.5 py-0.5">
                inactif
              </span>
            )}
          </div>
          {lastTest !== null && (
            <div className="text-xs flex items-center gap-1 mt-1">
              {lastTest.delivered ? (
                <>
                  <CheckCircle2 className="h-3 w-3 text-green-600" />
                  <span className="text-green-600">Test envoyé.</span>
                </>
              ) : (
                <>
                  <XCircle className="h-3 w-3 text-destructive" />
                  <span className="text-destructive">L'envoi a échoué.</span>
                </>
              )}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onTest}
            disabled={test.isPending}
            className="text-xs rounded-md border px-2 py-1 hover:bg-muted disabled:opacity-50 flex items-center gap-1"
          >
            {test.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : null}
            Tester
          </button>
          <button
            onClick={() =>
              toggle.mutate({
                id: webhook.id,
                body: { is_active: !webhook.is_active },
              })
            }
            disabled={toggle.isPending}
            className="text-xs rounded-md border px-2 py-1 hover:bg-muted disabled:opacity-50"
          >
            {webhook.is_active ? "Désactiver" : "Activer"}
          </button>
          <button
            onClick={() => del.mutate(webhook.id)}
            disabled={del.isPending}
            className="text-xs rounded-md border px-2 py-1 hover:bg-destructive/10 hover:text-destructive disabled:opacity-50 flex items-center gap-1"
            aria-label="Supprimer"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export function WebhooksPage() {
  const { data: webhooks, isLoading } = useWebhooksList();

  return (
    <AppShell>
      <main className="container py-8 space-y-8 max-w-2xl">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Webhooks</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Recevez une notification Slack ou Discord à chaque scan terminé.
          </p>
        </div>

        <AddWebhookForm />

        <div className="space-y-3">
          <h2 className="font-semibold">Webhooks existants</h2>
          {isLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="h-4 w-4 animate-spin" /> Chargement…
            </div>
          ) : !webhooks || webhooks.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Aucun webhook. Ajoutez-en un ci-dessus.
            </p>
          ) : (
            <div className="space-y-2">
              {webhooks.map((w) => (
                <WebhookCard key={w.id} webhook={w} />
              ))}
            </div>
          )}
        </div>
      </main>
    </AppShell>
  );
}
