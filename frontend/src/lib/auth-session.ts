import { getAccessToken, getRefreshToken } from "@/lib/cookies";
import { useAuthStore } from "@/stores/auth-store";

let refreshPromise: Promise<string | null> | null = null;

function buildRefreshPayload() {
  return {
    access_token: getAccessToken() ?? "",
    refresh_token: getRefreshToken() ?? "",
    token_type: "bearer",
  };
}

export function getPreferredAccessToken(
  token?: string | null,
): string | undefined {
  return getAccessToken() ?? token ?? undefined;
}

export async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    useAuthStore.getState().logout();
    return null;
  }

  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const response = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildRefreshPayload()),
        credentials: "include",
      });

      if (!response.ok) {
        useAuthStore.getState().logout();
        return null;
      }

      const tokens = (await response.json()) as {
        access_token: string;
        refresh_token: string;
      };
      useAuthStore
        .getState()
        .setTokens(tokens.access_token, tokens.refresh_token);
      return tokens.access_token;
    } catch {
      useAuthStore.getState().logout();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}
