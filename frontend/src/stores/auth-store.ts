import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoadingSession: boolean;

  setUser: (user: User | null) => void;
  setLoadingSession: (isLoadingSession: boolean) => void;
  login: (user: User) => void;
  logout: () => void;
  initialize: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoadingSession: true,

      setUser: (user: User | null) => {
        set({ user, isAuthenticated: Boolean(user) });
      },

      setLoadingSession: (isLoadingSession: boolean) => {
        set({ isLoadingSession });
      },

      login: (user: User) => {
        set({ user, isAuthenticated: true, isLoadingSession: false });
      },

      logout: () => {
        set({ user: null, isAuthenticated: false, isLoadingSession: false });
      },

      initialize: () => {
        set({ isLoadingSession: true });
      },
    }),
    {
      name: "astrotype-auth",
      partialize: (state) => ({ user: state.user }),
      onRehydrateStorage: () => (state) => {
        state?.setLoadingSession(false);
      },
    },
  ),
);
