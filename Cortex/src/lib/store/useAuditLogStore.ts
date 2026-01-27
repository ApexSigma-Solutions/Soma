import { create } from 'zustand';

export type AuditAction = 'capture' | 'ingest' | 'search' | 'login' | 'logout' | 'alert' | 'error';

export interface AuditLogEntry {
  id: string;
  timestamp: Date;
  action: AuditAction;
  description: string;
  user?: string;
  metadata?: Record<string, unknown>;
}

interface AuditLogStore {
  logs: AuditLogEntry[];
  addLog: (action: AuditAction, description: string, metadata?: Record<string, unknown>) => void;
  clearLogs: () => void;
}

const MAX_LOGS = 100;

export const useAuditLogStore = create<AuditLogStore>((set) => ({
  logs: [],
  addLog: (action, description, metadata) => {
    const entry: AuditLogEntry = {
      id: crypto.randomUUID(),
      timestamp: new Date(),
      action,
      description,
      metadata,
    };
    set((state) => ({
      logs: [entry, ...state.logs].slice(0, MAX_LOGS),
    }));
  },
  clearLogs: () => set({ logs: [] }),
}));

// Helper for logging
export const auditLog = {
  capture: (desc: string, meta?: Record<string, unknown>) => 
    useAuditLogStore.getState().addLog('capture', desc, meta),
  ingest: (desc: string, meta?: Record<string, unknown>) => 
    useAuditLogStore.getState().addLog('ingest', desc, meta),
  search: (desc: string, meta?: Record<string, unknown>) => 
    useAuditLogStore.getState().addLog('search', desc, meta),
  login: (desc: string, meta?: Record<string, unknown>) => 
    useAuditLogStore.getState().addLog('login', desc, meta),
  error: (desc: string, meta?: Record<string, unknown>) => 
    useAuditLogStore.getState().addLog('error', desc, meta),
};
