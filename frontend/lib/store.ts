"use client";

import { create } from "zustand";
import type { UserRead } from "@/types/api";
import { api, getToken } from "@/lib/api";

interface AuthState {
  user: UserRead | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    enrollment_no?: string;
    department_id?: string;
    program_name?: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  fetchUser: () => Promise<void>;
  setUser: (user: UserRead | null) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,

  login: async (email, password, rememberMe = false) => {
    const result = await api.auth.login(email, password, rememberMe);
    set({ user: result.user, isAuthenticated: true });
  },

  register: async (data) => {
    await api.auth.register(data);
  },

  logout: async () => {
    await api.auth.logout();
    set({ user: null, isAuthenticated: false });
  },

  fetchUser: async () => {
    if (!getToken()) {
      set({ isLoading: false, isAuthenticated: false });
      return;
    }
    try {
      const user = await api.auth.getMe();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  setUser: (user) => set({ user, isAuthenticated: !!user }),
}));
