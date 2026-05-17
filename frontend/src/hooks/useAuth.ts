import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { api } from "@/lib/api";
import { tokenStorage } from "@/lib/auth";
import type { TokenPair, User } from "@/types";

export function useCurrentUser() {
  return useQuery<User>({
    queryKey: ["me"],
    queryFn: () => api.get<User>("/api/v1/auth/me"),
    enabled: !!tokenStorage.getAccess(),
    retry: false,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { email: string; password: string }) =>
      api.post<TokenPair>("/api/v1/auth/login", data, true),
    onSuccess: (tokens) => {
      tokenStorage.set(tokens.access_token, tokens.refresh_token);
      void queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (data: { email: string; password: string; full_name?: string }) =>
      api.post<User>("/api/v1/auth/register", data, true),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  return () => {
    tokenStorage.clear();
    queryClient.clear();
    void navigate("/login");
  };
}
