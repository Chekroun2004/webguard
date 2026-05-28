import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { AuditEventList, AuditFilters } from "@/types/audit";

function buildQuery(filters: AuditFilters): string {
  const params = new URLSearchParams();
  params.set("page", String(filters.page));
  params.set("page_size", String(filters.pageSize));
  if (filters.action) params.set("action", filters.action);
  if (filters.status) params.set("status", filters.status);
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  return params.toString();
}

export function useAuditEvents(filters: AuditFilters) {
  return useQuery<AuditEventList>({
    queryKey: ["audit", filters],
    queryFn: () => api.get<AuditEventList>(`/api/v1/audit?${buildQuery(filters)}`),
  });
}
