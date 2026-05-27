import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { LoginPage } from "./LoginPage";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => mockNavigate };
});

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
    get: vi.fn(),
    post: vi.fn(),
    postNoContent: vi.fn(),
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
        <LoginPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("navigates to /dashboard when no totp is required", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      access_token: "a",
      refresh_token: "r",
      token_type: "bearer",
      totp_required: false,
      pending_token: null,
    });

    renderPage();
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "u@test.com" },
    });
    fireEvent.change(screen.getByLabelText("Mot de passe"), {
      target: { value: "password" },
    });
    fireEvent.click(screen.getByText("Se connecter"));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("switches to TOTP step when totp_required is true", async () => {
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      access_token: null,
      refresh_token: null,
      token_type: "bearer",
      totp_required: true,
      pending_token: "pending-jwt",
    });

    renderPage();
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "u@test.com" },
    });
    fireEvent.change(screen.getByLabelText("Mot de passe"), {
      target: { value: "password" },
    });
    fireEvent.click(screen.getByText("Se connecter"));

    await waitFor(() => {
      expect(screen.getByText("Vérification 2FA")).toBeInTheDocument();
    });
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("submits pending_token + code on TOTP step", async () => {
    (api.post as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        access_token: null,
        refresh_token: null,
        token_type: "bearer",
        totp_required: true,
        pending_token: "pending-jwt",
      })
      .mockResolvedValueOnce({
        access_token: "a",
        refresh_token: "r",
        token_type: "bearer",
      });

    renderPage();
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "u@test.com" },
    });
    fireEvent.change(screen.getByLabelText("Mot de passe"), {
      target: { value: "password" },
    });
    fireEvent.click(screen.getByText("Se connecter"));

    const code = await screen.findByPlaceholderText("123456");
    fireEvent.change(code, { target: { value: "654321" } });
    fireEvent.click(screen.getByText("Valider"));

    await waitFor(() => {
      expect(api.post).toHaveBeenLastCalledWith(
        "/api/v1/auth/login/totp",
        { pending_token: "pending-jwt", code: "654321" },
        true,
      );
      expect(mockNavigate).toHaveBeenCalledWith("/dashboard");
    });
  });
});
