import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, vi, beforeAll } from 'vitest';
import React from 'react';

// Setup global mocks before all tests
beforeAll(() => {
  Object.defineProperty(globalThis, 'EventSource', {
    writable: true,
    value: vi.fn().mockImplementation(() => ({
      close: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  });
});

// Cleanup after each test case (e.g. clearing jsdom)
afterEach(() => {
  cleanup();
});

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver
class MockIntersectionObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: MockIntersectionObserver,
});

// Mock ResizeObserver
class MockResizeObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  value: MockResizeObserver,
});

// Mock EventSource
Object.defineProperty(globalThis, 'EventSource', {
  writable: true,
  value: vi.fn().mockImplementation(() => ({
    close: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })),
});

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
  CheckCircle: () => React.createElement('div', { 'data-testid': 'icon-check-circle' }),
  XCircle: () => React.createElement('div', { 'data-testid': 'icon-x-circle' }),
  AlertTriangle: () => React.createElement('div', { 'data-testid': 'icon-alert-triangle' }),
  Info: () => React.createElement('div', { 'data-testid': 'icon-info' }),
  Wifi: () => React.createElement('div', { 'data-testid': 'icon-wifi' }),
  WifiOff: () => React.createElement('div', { 'data-testid': 'icon-wifi-off' }),
  Bell: () => React.createElement('div', { 'data-testid': 'icon-bell' }),
  X: () => React.createElement('div', { 'data-testid': 'icon-x' }),
  Plus: () => React.createElement('div', { 'data-testid': 'icon-plus' }),
  Trash2: () => React.createElement('div', { 'data-testid': 'icon-trash-2' }),
  StickyNote: () => React.createElement('div', { 'data-testid': 'icon-sticky-note' }),
  ArrowUp: () => React.createElement('div', { 'data-testid': 'icon-arrow-up' }),
  Star: () => React.createElement('div', { 'data-testid': 'icon-star' }),
  Archive: () => React.createElement('div', { 'data-testid': 'icon-archive' }),
  Sparkles: () => React.createElement('div', { 'data-testid': 'icon-sparkles' }),
  Lightbulb: () => React.createElement('div', { 'data-testid': 'icon-lightbulb' }),
  Share2: () => React.createElement('div', { 'data-testid': 'icon-share-2' }),
  ZoomIn: () => React.createElement('div', { 'data-testid': 'icon-zoom-in' }),
  ZoomOut: () => React.createElement('div', { 'data-testid': 'icon-zoom-out' }),
  GitCommit: () => React.createElement('div', { 'data-testid': 'icon-git-commit' }),
  Shield: () => React.createElement('div', { 'data-testid': 'icon-shield' }),
  TrendingUp: () => React.createElement('div', { 'data-testid': 'icon-trending-up' }),
  MemoryStick: () => React.createElement('div', { 'data-testid': 'icon-memory-stick' }),
  ChevronLeft: () => React.createElement('div', { 'data-testid': 'icon-chevron-left' }),
  ChevronRight: () => React.createElement('div', { 'data-testid': 'icon-chevron-right' }),
  ChevronDown: () => React.createElement('div', { 'data-testid': 'icon-chevron-down' }),
  SlidersHorizontal: () => React.createElement('div', { 'data-testid': 'icon-sliders-horizontal' }),
  Pause: () => React.createElement('div', { 'data-testid': 'icon-pause' }),
  Webhook: () => React.createElement('div', { 'data-testid': 'icon-webhook' }),
  ArrowRight: () => React.createElement('div', { 'data-testid': 'icon-arrow-right' }),
  Circle: () => React.createElement('div', { 'data-testid': 'icon-circle' }),

}));
