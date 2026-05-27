import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export interface TotpStatus {
  enabled: boolean;
  pending_setup: boolean;
}

export interface TotpEnrollResponse {
  secret: string;
  otpauth_uri: string;
}

const KEY = ["totp-status"];

export function useTotpStatus() {
  return useQuery<TotpStatus>({
    queryKey: KEY,
    queryFn: () => api.get<TotpStatus>("/api/v1/auth/totp/status"),
  });
}

export function useTotpEnroll() {
  return useMutation<TotpEnrollResponse, Error, void>({
    mutationFn: () => api.post<TotpEnrollResponse>("/api/v1/auth/totp/enroll", {}),
  });
}

export function useTotpConfirm() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (code) => api.postNoContent("/api/v1/auth/totp/confirm", { code }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEY });
    },
  });
}

export function useTotpDisable() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (code) => api.postNoContent("/api/v1/auth/totp/disable", { code }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KEY });
    },
  });
}
