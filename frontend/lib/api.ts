/**
 * WASL API client.
 *
 * Wraps fetch with:
 * - Automatic Bearer token attachment from localStorage
 * - Auto-refresh when access token is expiring soon
 * - Redirect to /login on 401 (after refresh attempt fails)
 *
 * Usage:
 *   import { apiFetch } from "@/lib/api";
 *   const data = await apiFetch("/api/v1/merchants/profile");
 */

import {
  clearTokens,
  getAccessToken,
  isTokenExpiringSoon,
  refreshAccessToken,
} from "@/lib/auth";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ApiResponse<T = unknown> = {
  success: boolean;
  data: T | null;
  error: { code: string; message: string; details?: unknown } | null;
};

async function redirectToLogin(): Promise<never> {
  clearTokens();
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
  // Throw so callers know the request did not succeed
  throw new Error("Unauthenticated — redirecting to login");
}

/**
 * Make an authenticated API request.
 *
 * @param path    - API path, e.g. "/api/v1/merchants/profile"
 * @param options - standard fetch RequestInit options
 * @returns Parsed JSON response body
 */
export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  // Auto-refresh if token is expiring soon
  if (isTokenExpiringSoon()) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) {
      return redirectToLogin();
    }
  }

  const token = getAccessToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers ?? {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  let res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  // If 401 on first attempt, try one refresh then retry
  if (res.status === 401) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) {
      return redirectToLogin();
    }
    const newToken = getAccessToken();
    const retryHeaders: HeadersInit = {
      ...headers,
      Authorization: `Bearer ${newToken ?? ""}`,
    };
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: retryHeaders,
    });
    if (res.status === 401) {
      return redirectToLogin();
    }
  }

  // 204 No Content — return empty success
  if (res.status === 204) {
    return { success: true, data: null, error: null };
  }

  return (await res.json()) as ApiResponse<T>;
}

/**
 * Unauthenticated POST (register, login, refresh).
 */
export async function publicPost<T = unknown>(
  path: string,
  body: unknown
): Promise<ApiResponse<T>> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (res.status === 204) {
    return { success: true, data: null, error: null };
  }
  return (await res.json()) as ApiResponse<T>;
}
