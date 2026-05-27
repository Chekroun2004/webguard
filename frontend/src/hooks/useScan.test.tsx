import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi, beforeEach } from "vitest";
import type { ReactNode } from "react";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn().mockResolvedValue({
      id: 7,
      url: "https://example.com",
      status: "pending",
      created_at: "2026-05-27T00:00:00Z",
      finished_at: null,
      findings: [],
    }),
  },
}));

import { api } from "@/lib/api";
import { useCreateScan } from "./useScan";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("useCreateScan", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("posts url alone when no auth_config is provided", async () => {
    const { result } = renderHook(() => useCreateScan(), { wrapper });
    await result.current.mutateAsync({ url: "https://example.com" });
    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/api/v1/scans", {
        url: "https://example.com",
      });
    });
  });

  it("forwards cookie auth_config to the backend", async () => {
    const { result } = renderHook(() => useCreateScan(), { wrapper });
    await result.current.mutateAsync({
      url: "https://example.com",
      auth_config: { strategy: "cookie", name: "session", value: "tok" },
    });
    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/api/v1/scans", {
        url: "https://example.com",
        auth_config: { strategy: "cookie", name: "session", value: "tok" },
      });
    });
  });

  it("forwards form_login auth_config to the backend", async () => {
    const { result } = renderHook(() => useCreateScan(), { wrapper });
    await result.current.mutateAsync({
      url: "https://example.com",
      auth_config: {
        strategy: "form_login",
        login_url: "https://example.com/login",
        username_field: "email",
        password_field: "password",
        username: "alice",
        password: "secret",
      },
    });
    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/api/v1/scans", {
        url: "https://example.com",
        auth_config: {
          strategy: "form_login",
          login_url: "https://example.com/login",
          username_field: "email",
          password_field: "password",
          username: "alice",
          password: "secret",
        },
      });
    });
  });
});
