import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { ApiKeysPage } from "./ApiKeysPage";

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      public detail: string,
    ) {
      super(detail);
    }
  },
  api: {
    get: vi.fn().mockResolvedValue([]),
    post: vi.fn().mockResolvedValue({
      id: 1,
      name: "ci-bot",
      prefix: "wgk_abcd",
      key: "wgk_full-secret-plaintext-shown-once",
      last_used_at: null,
      created_at: "2026-05-27T00:00:00Z",
      revoked_at: null,
    }),
    del: vi.fn(),
  },
}));

import { api } from "@/lib/api";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ApiKeysPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ApiKeysPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits create with the typed name", async () => {
    renderPage();

    const name = await screen.findByPlaceholderText("ex: ci-bot, mon-cli");
    fireEvent.change(name, { target: { value: "ci-bot" } });
    fireEvent.click(screen.getByText("Générer"));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/api/v1/api-keys", { name: "ci-bot" });
    });
  });

  it("shows the plaintext key in the modal after creation", async () => {
    renderPage();

    fireEvent.change(await screen.findByPlaceholderText("ex: ci-bot, mon-cli"), {
      target: { value: "ci-bot" },
    });
    fireEvent.click(screen.getByText("Générer"));

    expect(
      await screen.findByText("wgk_full-secret-plaintext-shown-once"),
    ).toBeInTheDocument();
    expect(screen.getByText("Copiez cette clé maintenant")).toBeInTheDocument();
  });
});
