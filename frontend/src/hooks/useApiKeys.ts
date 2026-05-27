import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface ApiKey {
  id: number;
  name: string;
  prefix: string;
  last_used_at: string | null;
  created_at: string;
  revoked_at: string | null;
}

export interface ApiKeyCreated extends ApiKey {
  key: string;
}

const KEY = ["api-keys"];

export function useApiKeysList() {
  return useQuery<ApiKey[]>({
    queryKey: KEY,
    queryFn: () => api.get<ApiKey[]>("/api/v1/api-keys"),
  });
}

export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation<ApiKeyCreated, Error, string>({
    mutationFn: (name) =>
      api.post<ApiKeyCreated>("/api/v1/api-keys", { name }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEY });
    },
  });
}

export function useRevokeApiKey() {
  const qc = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: (id) => api.del(`/api/v1/api-keys/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEY });
    },
  });
}
