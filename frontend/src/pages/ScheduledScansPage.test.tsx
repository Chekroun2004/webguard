import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { ScheduledScansPage } from "./ScheduledScansPage";

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
      url: "https://example.com",
      cron_expression: "0 9 * * *",
      is_active: true,
      last_run_at: null,
      next_run_at: "2026-05-19T09:00:00Z",
      created_at: "2026-05-18T00:00:00Z",
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
        <ScheduledScansPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ScheduledScansPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits a daily preset as cron 0 9 * * *", async () => {
    renderPage();

    const urlInput = await screen.findByPlaceholderText("https://example.com");
    fireEvent.change(urlInput, { target: { value: "https://example.com" } });

    fireEvent.click(screen.getByText("Planifier"));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/api/v1/scheduled", {
        url: "https://example.com",
        cron_expression: "0 9 * * *",
      });
    });
  });
});
