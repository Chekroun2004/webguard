import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface ScheduledScan {
  id: number;
  url: string;
  cron_expression: string;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string;
  created_at: string;
}

export interface ScheduledScanCreateInput {
  url: string;
  cron_expression: string;
  is_active?: boolean;
}

export interface ScheduledScanUpdateInput {
  cron_expression?: string;
  is_active?: boolean;
}

const KEY = ["scheduled-scans"];

export function useScheduledScansList() {
  return useQuery<ScheduledScan[]>({
    queryKey: KEY,
    queryFn: () => api.get<ScheduledScan[]>("/api/v1/scheduled"),
  });
}

export function useCreateScheduledScan() {
  const qc = useQueryClient();
  return useMutation<ScheduledScan, Error, ScheduledScanCreateInput>({
    mutationFn: (body) => api.post<ScheduledScan>("/api/v1/scheduled", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEY });
    },
  });
}

export function useUpdateScheduledScan() {
  const qc = useQueryClient();
  return useMutation<
    ScheduledScan,
    Error,
    { id: number; body: ScheduledScanUpdateInput }
  >({
    mutationFn: ({ id, body }) =>
      api.patch<ScheduledScan>(`/api/v1/scheduled/${id}`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEY });
    },
  });
}

export function useDeleteScheduledScan() {
  const qc = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: (id) => api.del(`/api/v1/scheduled/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEY });
    },
  });
}
