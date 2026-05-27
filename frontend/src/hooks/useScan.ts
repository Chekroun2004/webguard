import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Scan } from "@/types";

export type ScanAuthConfig =
  | { strategy: "cookie"; name: string; value: string }
  | {
      strategy: "form_login";
      login_url: string;
      username_field: string;
      password_field: string;
      username: string;
      password: string;
    };

export interface CreateScanInput {
  url: string;
  auth_config?: ScanAuthConfig;
}

export function useScanList() {
  return useQuery<Scan[]>({
    queryKey: ["scans"],
    queryFn: () => api.get<Scan[]>("/api/v1/scans"),
  });
}

export function useScan(id: number | null) {
  return useQuery<Scan>({
    queryKey: ["scans", id],
    queryFn: () => api.get<Scan>(`/api/v1/scans/${id}`),
    enabled: id !== null,
  });
}

export function useCreateScan() {
  const qc = useQueryClient();
  return useMutation<Scan, Error, CreateScanInput>({
    mutationFn: (body) => api.post<Scan>("/api/v1/scans", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["scans"] });
    },
  });
}
