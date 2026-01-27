import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { ApiHealth } from '@/lib/api/client';

interface SystemState {
  // API Health State
  apiHealth: ApiHealth[];
  setApiHealth: (health: ApiHealth[]) => void;

  // UI State
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;
  toggleTheme: () => void;

  // System Info
  systemStatus: 'online' | 'degraded' | 'offline';
  updateSystemStatus: () => void;
}

export const useSystemStore = create<SystemState>()(
  devtools(
    persist(
      (set, get) => ({
        // API Health State
        apiHealth: [],
        setApiHealth: (health) => {
          set({ apiHealth: health }, false, 'setApiHealth');
          get().updateSystemStatus();
        },

        // UI State
        sidebarCollapsed: false,
        toggleSidebar: () =>
          set(
            (state) => ({ sidebarCollapsed: !state.sidebarCollapsed }),
            false,
            'toggleSidebar'
          ),
        
        theme: 'dark', // Default to dark (brand preference)
        setTheme: (theme) => {
          set({ theme }, false, 'setTheme');
          // Apply theme to document
          if (theme === 'dark') {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
        },
        toggleTheme: () => {
          const currentTheme = get().theme;
          const newTheme = currentTheme === 'light' ? 'dark' : 'light';
          get().setTheme(newTheme);
        },

        // System Status
        systemStatus: 'offline',
        updateSystemStatus: () => {
          const { apiHealth } = get();

          if (apiHealth.length === 0) {
            set({ systemStatus: 'offline' }, false, 'updateSystemStatus/offline');
            return;
          }

          const healthyCount = apiHealth.filter((api) => api.healthy).length;
          const totalCount = apiHealth.length;

          if (healthyCount === totalCount) {
            set({ systemStatus: 'online' }, false, 'updateSystemStatus/online');
          } else if (healthyCount > 0) {
            set({ systemStatus: 'degraded' }, false, 'updateSystemStatus/degraded');
          } else {
            set({ systemStatus: 'offline' }, false, 'updateSystemStatus/offline');
          }
        },
      }),
      {
        name: 'cortex-bridge-storage',
        partialize: (state) => ({
          sidebarCollapsed: state.sidebarCollapsed,
          theme: state.theme,
        }), // Only persist UI state, not ephemeral health data
      }
    )
  )
);
