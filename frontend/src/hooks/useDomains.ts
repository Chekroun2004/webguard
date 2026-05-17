import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type VerificationMethod = "file" | "dns";

export interface Domain {
  id: number;
  domain: string;
  verification_method: VerificationMethod;
  verification_token: string;
  is_verified: boolean;
  verified_at: string | null;
  created_at: string;
}

export function useDomainList() {
  return useQuery<Domain[]>({
    queryKey: ["domains"],
    queryFn: () => api.get<Domain[]>("/api/v1/domains"),
  });
}

export function useRegisterDomain() {
  const qc = useQueryClient();
  return useMutation<Domain, Error, { domain: string; method: VerificationMethod }>({
    mutationFn: (body) => api.post<Domain>("/api/v1/domains", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["domains"] });
    },
  });
}

export function useVerifyDomain() {
  const qc = useQueryClient();
  return useMutation<Domain, Error, number>({
    mutationFn: (id) => api.post<Domain>(`/api/v1/domains/${id}/verify`, {}),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["domains"] });
    },
  });
}
