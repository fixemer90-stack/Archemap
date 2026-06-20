type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  retryOnAuthFailure?: boolean;
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

function buildRequestInit(options: RequestOptions): RequestInit {
  const { method = "GET", body, headers = {} } = options;
  const requestHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...headers,
  };

  return {
    method,
    headers: requestHeaders,
    body: body ? JSON.stringify(body) : undefined,
    credentials: "include",
  };
}

async function tryCookieRefresh(): Promise<boolean> {
  try {
    const response = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
      credentials: "include",
    });
    return response.ok;
  } catch {
    return false;
  }
}

async function fetchWithAuthRetry(
  endpoint: string,
  options: RequestOptions = {},
): Promise<Response> {
  const response = await fetch(endpoint, buildRequestInit(options));

  if (
    response.status !== 401 ||
    isAuthEndpoint(endpoint) ||
    options.retryOnAuthFailure === false
  ) {
    return response;
  }

  const refreshed = await tryCookieRefresh();
  if (!refreshed) {
    return response;
  }

  return fetch(endpoint, buildRequestInit(options));
}

// Always use relative paths — Next.js rewrites proxy to backend.
// Browser auth is cookie-first: protected requests use credentials: "include"
// and never attach Authorization by default.
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
  get: <T>(endpoint: string) => apiClient<T>(endpoint),

  post: <T>(endpoint: string, body: unknown) =>
    apiClient<T>(endpoint, { method: "POST", body }),

  put: <T>(endpoint: string, body: unknown) =>
    apiClient<T>(endpoint, { method: "PUT", body }),

  patch: <T>(endpoint: string, body: unknown) =>
    apiClient<T>(endpoint, { method: "PATCH", body }),

  delete: <T>(endpoint: string) => apiClient<T>(endpoint, { method: "DELETE" }),
};
