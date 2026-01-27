import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user';
}

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  register: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      token: null,
      user: null,
      login: (token, user) => set({ isAuthenticated: true, token, user }),
      logout: () => set({ isAuthenticated: false, token: null, user: null }),
      register: (user) => {
         // In a real app, this would hit an API.
         // Here we just simulate auto-login after "registration"
         const token = `mock-jwt-${crypto.randomUUID()}`;
         set({ isAuthenticated: true, token, user });
      }
    }),
    {
      name: 'auth-storage',
    }
  )
);
