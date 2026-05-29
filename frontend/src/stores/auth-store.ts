import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  getAccessToken,
  setAccessToken,
  removeAccessToken,
  clearAllTokens,
} from "@/lib/cookies";

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (user: User, token: string) => void;
  logout: () => void;
  setUser: (user: User) => void;
  setLoading: (loading: boolean) => void;
  initialize: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: getAccessToken() || null,
      isAuthenticated: !!getAccessToken(),
      isLoading: false,

      login: (user: User, token: string) => {
        setAccessToken(token);
        set({
          user,
          token,
          isAuthenticated: true,
          isLoading: false,
        });
      },

      logout: () => {
        clearAllTokens();
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
        });
      },

      setUser: (user: User) => {
        set({ user });
      },

      setLoading: (isLoading: boolean) => {
        set({ isLoading });
      },

      initialize: () => {
        const token = getAccessToken();
        set({
          token: token || null,
          isAuthenticated: !!token,
        });
      },
    }),
    {
      name: "archemap-auth",
      partialize: (state) => ({
        user: state.user,
      }),
    },
  ),
);
