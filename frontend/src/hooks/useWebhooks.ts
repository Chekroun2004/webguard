import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type WebhookProvider = "slack" | "discord";

export interface Webhook {
  id: number;
  url: string;
  provider: WebhookProvider;
  is_active: boolean;
  created_at: string;
}

export interface WebhookCreateInput {
  url: string;
  provider: WebhookProvider;
  is_active?: boolean;
}

export interface WebhookUpdateInput {
  url?: string;
  provider?: WebhookProvider;
  is_active?: boolean;
}

const KEY = ["webhooks"];

export function useWebhooksList() {
  return useQuery<Webhook[]>({
    queryKey: KEY,
    queryFn: () => api.get<Webhook[]>("/api/v1/webhooks"),
  });
}

export function useCreateWebhook() {
  const qc = useQueryClient();
  return useMutation<Webhook, Error, WebhookCreateInput>({
    mutationFn: (body) => api.post<Webhook>("/api/v1/webhooks", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEY });
    },
  });
}

export function useUpdateWebhook() {
  const qc = useQueryClient();
  return useMutation<Webhook, Error, { id: number; body: WebhookUpdateInput }>({
    mutationFn: ({ id, body }) =>
      api.patch<Webhook>(`/api/v1/webhooks/${id}`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEY });
    },
  });
}

export function useDeleteWebhook() {
  const qc = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: (id) => api.del(`/api/v1/webhooks/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEY });
    },
  });
}

export function useTestWebhook() {
  return useMutation<{ delivered: boolean }, Error, number>({
    mutationFn: (id) =>
      api.post<{ delivered: boolean }>(`/api/v1/webhooks/${id}/test`, {}),
  });
}
