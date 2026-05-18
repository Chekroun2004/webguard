import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { ScanDiff } from "@/types";

export function useScanDiff(oldId: number | null, newId: number | null) {
  return useQuery<ScanDiff>({
    queryKey: ["scan-diff", oldId, newId],
    queryFn: () => api.get<ScanDiff>(`/api/v1/scans/diff?old=${oldId}&new=${newId}`),
    enabled: oldId !== null && newId !== null && oldId !== newId,
  });
}
