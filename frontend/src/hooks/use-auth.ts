"use client";

import { useAuthStore } from "@/stores/auth-store";

export function useAuth() {
  const { user, token, isAuthenticated, login, logout, setUser } =
    useAuthStore();

  return { user, token, isAuthenticated, login, logout, setUser };
}
