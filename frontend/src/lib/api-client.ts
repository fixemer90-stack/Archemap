import { getPreferredAccessToken, refreshAccessToken } from "@/lib/auth-session";

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  token?: string;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public data?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function isAuthEndpoint(endpoint: string): boolean {
  return endpoint.startsWith("/api/v1/auth/");
}

function buildRequestInit(
  options: RequestOptions,
  tokenOverride?: string,
): RequestInit {
  const { method = "GET", body, headers = {} } = options;
  const effectiveToken = getPreferredAccessToken(tokenOverride ?? options.token);

  const requestHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...headers,
  };

  if (effectiveToken) {
    requestHeaders.Authorization = `Bearer ${effectiveToken}`;
  }

  return {
    method,
    headers: requestHeaders,
    body: body ? JSON.stringify(body) : undefined,
    credentials: "include",
  };
}

async function fetchWithAuthRetry(
  endpoint: string,
  options: RequestOptions = {},
): Promise<Response> {
  const firstAttemptToken = getPreferredAccessToken(options.token);
  let response = await fetch(endpoint, buildRequestInit(options, firstAttemptToken));

  if (response.status !== 401 || isAuthEndpoint(endpoint)) {
    return response;
  }

  const latestToken = getPreferredAccessToken();
  if (latestToken && latestToken !== firstAttemptToken) {
    response = await fetch(endpoint, buildRequestInit(options, latestToken));
    if (response.status !== 401) {
      return response;
    }
  }

  const refreshedToken = await refreshAccessToken();
  if (!refreshedToken) {
    return response;
  }

  return fetch(endpoint, buildRequestInit(options, refreshedToken));
}

// Always use relative paths — Next.js rewrites proxy to backend
export async function apiFetch(
  endpoint: string,
  options: RequestOptions = {},
): Promise<Response> {
  return fetchWithAuthRetry(endpoint, options);
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<T> {
  const response = await apiFetch(endpoint, options);

  if (!response.ok) {
    let data: unknown;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    throw new ApiError(
      response.status,
      (data as { detail?: string })?.detail || response.statusText,
      data,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  get: <T>(endpoint: string, token?: string) =>
    apiClient<T>(endpoint, { token }),

  post: <T>(endpoint: string, body: unknown, token?: string) =>
    apiClient<T>(endpoint, { method: "POST", body, token }),

  put: <T>(endpoint: string, body: unknown, token?: string) =>
    apiClient<T>(endpoint, { method: "PUT", body, token }),

  patch: <T>(endpoint: string, body: unknown, token?: string) =>
    apiClient<T>(endpoint, { method: "PATCH", body, token }),

  delete: <T>(endpoint: string, token?: string) =>
    apiClient<T>(endpoint, { method: "DELETE", token }),
};
