import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  mobileSidebarOpen: boolean;
  theme: "light" | "dark" | "system";

  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleMobileSidebar: () => void;
  setMobileSidebarOpen: (open: boolean) => void;
  setTheme: (theme: "light" | "dark" | "system") => void;
}

export const useUIStore = create<UIState>()((set) => ({
  sidebarOpen: true,
  mobileSidebarOpen: false,
  theme: "system",

  toggleSidebar: () => {
    set((state) => ({ sidebarOpen: !state.sidebarOpen }));
  },

  setSidebarOpen: (open: boolean) => {
    set({ sidebarOpen: open });
  },

  toggleMobileSidebar: () => {
    set((state) => ({ mobileSidebarOpen: !state.mobileSidebarOpen }));
  },

  setMobileSidebarOpen: (open: boolean) => {
    set({ mobileSidebarOpen: open });
  },

  setTheme: (theme: "light" | "dark" | "system") => {
    set({ theme });
  },
}));
