import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface AnalyticsMetrics {
  totalCaptures: number;
  totalIngestions: number;
  totalSearches: number;
  activeSessionMinutes: number;
  lastActivity: Date | null;
}

interface AnalyticsStore extends AnalyticsMetrics {
  incrementCaptures: () => void;
  incrementIngestions: () => void;
  incrementSearches: () => void;
  updateSessionTime: (minutes: number) => void;
  setMetrics: (metrics: Partial<AnalyticsMetrics>) => void;
  resetMetrics: () => void;
}

const defaultMetrics: AnalyticsMetrics = {
  totalCaptures: 0,
  totalIngestions: 0,
  totalSearches: 0,
  activeSessionMinutes: 0,
  lastActivity: null,
};

export const useAnalyticsStore = create<AnalyticsStore>()(
  persist(
    (set) => ({
      ...defaultMetrics,
      incrementCaptures: () =>
        set((state) => ({
          totalCaptures: state.totalCaptures + 1,
          lastActivity: new Date(),
        })),
      incrementIngestions: () =>
        set((state) => ({
          totalIngestions: state.totalIngestions + 1,
          lastActivity: new Date(),
        })),
      incrementSearches: () =>
        set((state) => ({
          totalSearches: state.totalSearches + 1,
          lastActivity: new Date(),
        })),
      updateSessionTime: (minutes) =>
        set((state) => ({
          activeSessionMinutes: state.activeSessionMinutes + minutes,
        })),
      setMetrics: (metrics) =>
        set((state) => ({
          ...state,
          ...metrics,
        })),
      resetMetrics: () => set(defaultMetrics),
    }),
    {
      name: 'cortex-analytics',
    }
  )
);
