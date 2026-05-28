import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { AuditPage } from "./AuditPage";

const getMock = vi.fn();

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
    get: (path: string) => getMock(path),
    post: vi.fn(),
    patch: vi.fn(),
    del: vi.fn(),
  },
}));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuditPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const threeEvents = {
  items: [
    {
      id: 3,
      user_id: 1,
      action: "scan.create",
      target_type: "scan",
      target_id: 9,
      status: "success",
      ip: "127.0.0.1",
      user_agent: "curl/8",
      created_at: "2026-05-27T10:00:00Z",
    },
    {
      id: 2,
      user_id: 1,
      action: "webhook.delete",
      target_type: "webhook",
      target_id: 5,
      status: "failure",
      ip: "127.0.0.1",
      user_agent: "Mozilla/5.0",
      created_at: "2026-05-27T09:00:00Z",
    },
    {
      id: 1,
      user_id: 1,
      action: "totp.enable",
      target_type: null,
      target_id: null,
      status: "success",
      ip: null,
      user_agent: null,
      created_at: "2026-05-27T08:00:00Z",
    },
  ],
  total: 3,
  page: 1,
  page_size: 50,
};

describe("AuditPage", () => {
  beforeEach(() => {
    getMock.mockReset();
  });

  it("affiche la liste d'événements", async () => {
    getMock.mockResolvedValue(threeEvents);
    renderPage();
    expect(await screen.findByText("Création scan")).toBeInTheDocument();
    expect(screen.getByText("Suppression webhook")).toBeInTheDocument();
    expect(screen.getByText("Activation 2FA")).toBeInTheDocument();
  });

  it("affiche l'empty state quand aucun événement", async () => {
    getMock.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
    renderPage();
    expect(
      await screen.findByText("Aucune activité enregistrée."),
    ).toBeInTheDocument();
  });

  it("change le filtre action et relance la requête avec le param", async () => {
    getMock.mockResolvedValue(threeEvents);
    renderPage();
    // wait for first load
    await screen.findByText("Création scan");

    // The first <select> on the page is the action filter.
    const selects = screen.getAllByRole("combobox");
    fireEvent.change(selects[0], { target: { value: "webhook.delete" } });

    await waitFor(() => {
      const calledWith = getMock.mock.calls.map((c) => c[0] as string);
      expect(
        calledWith.some((url) => url.includes("action=webhook.delete")),
      ).toBe(true);
    });
  });
});
