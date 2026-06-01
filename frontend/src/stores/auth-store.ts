import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  getAccessToken,
  setAccessToken,
  setRefreshToken,
  clearAllTokens,
} from "@/lib/cookies";

export interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;

  setTokens: (accessToken: string, refreshToken: string) => void;
  setUser: (user: User) => void;
  login: (user: User, token: string) => void;
  logout: () => void;
  initialize: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: getAccessToken() || null,
      isAuthenticated: !!getAccessToken(),

      setTokens: (accessToken: string, refreshToken: string) => {
        setAccessToken(accessToken);
        setRefreshToken(refreshToken);
        set({ token: accessToken, isAuthenticated: true });
      },

      setUser: (user: User) => {
        set({ user });
      },

      login: (user: User, token: string) => {
        setAccessToken(token);
        set({ user, token, isAuthenticated: true });
      },

      logout: () => {
        clearAllTokens();
        set({ user: null, token: null, isAuthenticated: false });
      },

      initialize: () => {
        const token = getAccessToken();
        set({ token: token || null, isAuthenticated: !!token });
      },
    }),
    {
      name: "astrotype-auth",
      partialize: (state) => ({ user: state.user }),
    },
  ),
);
