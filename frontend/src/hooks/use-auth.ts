"use client";

import { useAuthStore } from "@/stores/auth-store";

export function useAuth() {
  const { user, isAuthenticated, isLoadingSession, login, logout, setUser } =
    useAuthStore();

  return { user, isAuthenticated, isLoadingSession, login, logout, setUser };
}
