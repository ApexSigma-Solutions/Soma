import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Cleanup after each test case (e.g. clearing jsdom)
afterEach(() => {
  cleanup();
});

import React from 'react';
import { vi } from 'vitest';

// Mock lucide-react with explicit icons to avoid Proxy hangs
vi.mock('lucide-react', () => ({
  Loader2: () => React.createElement('div', { 'data-testid': 'icon-loader' }),
  Search: () => React.createElement('div', { 'data-testid': 'icon-search' }),
  Brain: () => React.createElement('div', { 'data-testid': 'icon-brain' }),
  Database: () => React.createElement('div', { 'data-testid': 'icon-database' }),
  FileText: () => React.createElement('div', { 'data-testid': 'icon-file-text' }),
  Layers: () => React.createElement('div', { 'data-testid': 'icon-layers' }),
  Play: () => React.createElement('div', { 'data-testid': 'icon-play' }),
  Activity: () => React.createElement('div', { 'data-testid': 'icon-activity' }),
  Cpu: () => React.createElement('div', { 'data-testid': 'icon-cpu' }),
  Clock: () => React.createElement('div', { 'data-testid': 'icon-clock' }),
  CheckCircle2: () => React.createElement('div', { 'data-testid': 'icon-check-circle' }),
  AlertCircle: () => React.createElement('div', { 'data-testid': 'icon-alert-circle' }),
  Send: () => React.createElement('div', { 'data-testid': 'icon-send' }),
  HardDrive: () => React.createElement('div', { 'data-testid': 'icon-hard-drive' }),
  Server: () => React.createElement('div', { 'data-testid': 'icon-server' }),
  Inbox: () => React.createElement('div', { 'data-testid': 'icon-inbox' }),
  FolderSearch: () => React.createElement('div', { 'data-testid': 'icon-folder-search' }),
  ClipboardList: () => React.createElement('div', { 'data-testid': 'icon-clipboard-list' }),
  Upload: () => React.createElement('div', { 'data-testid': 'icon-upload' }),
  RefreshCw: () => React.createElement('div', { 'data-testid': 'icon-refresh-cw' }),
}));
