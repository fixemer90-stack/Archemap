import Cookies from "js-cookie";

const TOKEN_KEY = "archemap_token";
const REFRESH_TOKEN_KEY = "archemap_refresh_token";

export function getAccessToken(): string | undefined {
  return Cookies.get(TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  Cookies.set(TOKEN_KEY, token, {
    expires: 1, // 1 day
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
  });
}

export function removeAccessToken(): void {
  Cookies.remove(TOKEN_KEY);
}

export function getRefreshToken(): string | undefined {
  return Cookies.get(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string): void {
  Cookies.set(REFRESH_TOKEN_KEY, token, {
    expires: 30, // 30 days
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
  });
}

export function removeRefreshToken(): void {
  Cookies.remove(REFRESH_TOKEN_KEY);
}

export function clearAllTokens(): void {
  removeAccessToken();
  removeRefreshToken();
}
