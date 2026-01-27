import { create } from 'zustand';

export type AlertSeverity = 'info' | 'warning' | 'critical';

export interface SystemAlert {
  id: string;
  title: string;
  message: string;
  severity: AlertSeverity;
  service?: 'omega' | 'ingest' | 'memos';
  dismissed: boolean;
  createdAt: Date;
}

interface AlertStore {
  alerts: SystemAlert[];
  addAlert: (alert: Omit<SystemAlert, 'id' | 'dismissed' | 'createdAt'>) => void;
  dismissAlert: (id: string) => void;
  clearAlerts: () => void;
}

export const useAlertStore = create<AlertStore>((set) => ({
  alerts: [],
  addAlert: (alert) => {
    const newAlert: SystemAlert = {
      ...alert,
      id: crypto.randomUUID(),
      dismissed: false,
      createdAt: new Date(),
    };
    set((state) => ({
      alerts: [newAlert, ...state.alerts.filter(a => !a.dismissed)],
    }));
  },
  dismissAlert: (id) =>
    set((state) => ({
      alerts: state.alerts.map((a) =>
        a.id === id ? { ...a, dismissed: true } : a
      ),
    })),
  clearAlerts: () => set({ alerts: [] }),
}));
