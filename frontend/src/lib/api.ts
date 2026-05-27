import { tokenStorage } from "./auth";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  skipAuth = false,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (!skipAuth) {
    const token = tokenStorage.getAccess();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = typeof body.detail === "string" ? body.detail : res.statusText;
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

async function requestNoContent(path: string, options: RequestInit = {}): Promise<void> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const token = tokenStorage.getAccess();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = typeof body.detail === "string" ? body.detail : res.statusText;
    throw new ApiError(res.status, detail);
  }
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown, skipAuth = false) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }, skipAuth),
  postNoContent: (path: string, body: unknown) =>
    requestNoContent(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  del: (path: string) => requestNoContent(path, { method: "DELETE" }),
};
