/**
 * WASL auth token management.
 *
 * Tokens are stored in localStorage (client-side only).
 * Auto-refresh is triggered when the access token has less
 * than 5 minutes remaining before expiry.
 *
 * Never log or expose token values.
 */

const ACCESS_TOKEN_KEY = "wasl_access_token";
const REFRESH_TOKEN_KEY = "wasl_refresh_token";
const EXPIRES_AT_KEY = "wasl_expires_at";

// ── Storage helpers ───────────────────────────────────────────────────────

export function saveTokens(
  accessToken: string,
  refreshToken: string,
  expiresIn: number // seconds
): void {
  const expiresAt = Date.now() + expiresIn * 1000;
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  localStorage.setItem(EXPIRES_AT_KEY, String(expiresAt));
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(EXPIRES_AT_KEY);
}

export function isLoggedIn(): boolean {
  return getAccessToken() !== null;
}

function getExpiresAt(): number {
  const v = localStorage.getItem(EXPIRES_AT_KEY);
  return v ? parseInt(v, 10) : 0;
}

/** Returns true if the access token expires within 5 minutes. */
export function isTokenExpiringSoon(): boolean {
  const expiresAt = getExpiresAt();
  if (!expiresAt) return false;
  return Date.now() > expiresAt - 5 * 60 * 1000;
}

// ── Auto-refresh ──────────────────────────────────────────────────────────

let _refreshPromise: Promise<boolean> | null = null;

/**
 * Attempt to refresh the access token using the stored refresh token.
 * Returns true on success, false on failure (caller should redirect to login).
 * Concurrent calls share the same in-flight promise.
 */
export async function refreshAccessToken(): Promise<boolean> {
  if (_refreshPromise) return _refreshPromise;

  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  _refreshPromise = (async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) {
        clearTokens();
        return false;
      }
      const body = await res.json();
      const { token, refresh_token: newRefresh, expires_in } = body.data;
      saveTokens(token, newRefresh, expires_in);
      return true;
    } catch {
      return false;
    } finally {
      _refreshPromise = null;
    }
  })();

  return _refreshPromise;
}

export async function logout(refreshToken: string): Promise<void> {
  const accessToken = getAccessToken();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    await fetch(`${apiUrl}/api/v1/auth/logout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken ?? ""}`,
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } finally {
    clearTokens();
  }
}
