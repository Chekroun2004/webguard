import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Scan } from "@/types";

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
  return useMutation<Scan, Error, string>({
    mutationFn: (url: string) =>
      api.post<Scan>("/api/v1/scans", { url }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["scans"] });
    },
  });
}
