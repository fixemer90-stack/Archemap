import { useAuthStore, type User } from "@/stores/auth-store";

let refreshPromise: Promise<boolean> | null = null;

async function fetchCurrentUser(): Promise<User | null> {
  const response = await fetch("/api/v1/users/me", {
    method: "GET",
    credentials: "include",
  });
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as User;
}

export async function refreshSession(): Promise<boolean> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const refreshResponse = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
        credentials: "include",
      });
      if (!refreshResponse.ok) {
        return false;
      }
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export async function bootstrapSession(): Promise<User | null> {
  const store = useAuthStore.getState();
  store.setLoadingSession(true);
  try {
    const currentUser = await fetchCurrentUser();
    if (currentUser) {
      store.login(currentUser);
      return currentUser;
    }

    const refreshed = await refreshSession();
    if (!refreshed) {
      store.logout();
      return null;
    }

    const userAfterRefresh = await fetchCurrentUser();
    if (userAfterRefresh) {
      store.login(userAfterRefresh);
      return userAfterRefresh;
    }

    store.logout();
    return null;
  } finally {
    useAuthStore.getState().setLoadingSession(false);
  }
}
