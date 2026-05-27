import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { WebhooksPage } from "./WebhooksPage";

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
      url: "https://hooks.slack.com/services/T000/B000/xxx",
      provider: "slack",
      is_active: true,
      created_at: "2026-05-27T00:00:00Z",
    }),
    patch: vi.fn(),
    del: vi.fn(),
  },
}));

import { api } from "@/lib/api";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <WebhooksPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("WebhooksPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits a Slack webhook with provider=slack", async () => {
    renderPage();

    const urlInput = await screen.findByPlaceholderText(
      "https://hooks.slack.com/services/T000/B000/xxx",
    );
    fireEvent.change(urlInput, {
      target: { value: "https://hooks.slack.com/services/T000/B000/xxx" },
    });

    fireEvent.click(screen.getByText("Ajouter"));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/api/v1/webhooks", {
        url: "https://hooks.slack.com/services/T000/B000/xxx",
        provider: "slack",
      });
    });
  });

  it("switches placeholder when selecting Discord", async () => {
    renderPage();
    await screen.findByText("Ajouter un webhook");
    fireEvent.click(screen.getByLabelText("Discord"));
    expect(
      screen.getByPlaceholderText("https://discord.com/api/webhooks/123/abc"),
    ).toBeInTheDocument();
  });
});
