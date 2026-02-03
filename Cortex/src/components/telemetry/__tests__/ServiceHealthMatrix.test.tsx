import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ServiceHealthMatrix } from '@/components/telemetry/ServiceHealthMatrix';
import { useSystemStore } from '@/lib/store/systemStore';

vi.mock('@/lib/store/systemStore');

describe('ServiceHealthMatrix', () => {
  it('should display all services with correct status', () => {
    const mockHealth = [
      { name: 'InGress', healthy: true, latency: 45 },
      { name: 'InGest', healthy: true, latency: 120 },
      { name: 'Omega', healthy: false, error: 'Connection timeout' },
      { name: 'Memos', healthy: true, latency: 80 },
    ];

    vi.mocked(useSystemStore).mockReturnValue({
      apiHealth: mockHealth,
      sidebarCollapsed: false,
      theme: 'dark',
      systemStatus: 'degraded',
      setApiHealth: vi.fn(),
      toggleSidebar: vi.fn(),
      setTheme: vi.fn(),
      toggleTheme: vi.fn(),
      updateSystemStatus: vi.fn(),
    });

    render(<ServiceHealthMatrix />);

    expect(screen.getByText('InGress')).toBeInTheDocument();
    expect(screen.getByText('InGest')).toBeInTheDocument();
    expect(screen.getByText('Omega')).toBeInTheDocument();
    expect(screen.getByText('Memos')).toBeInTheDocument();

    expect(screen.getByText('8000')).toBeInTheDocument();
    expect(screen.getByText('8766')).toBeInTheDocument();
    expect(screen.getByText('8765')).toBeInTheDocument();
    expect(screen.getByText('8768')).toBeInTheDocument();
  });

  it('should show correct status colors', () => {
    const mockHealth = [
      { name: 'InGress', healthy: true, latency: 45 },
      { name: 'Omega', healthy: false, error: 'Connection timeout' },
    ];

    vi.mocked(useSystemStore).mockReturnValue({
      apiHealth: mockHealth,
      sidebarCollapsed: false,
      theme: 'dark',
      systemStatus: 'degraded',
      setApiHealth: vi.fn(),
      toggleSidebar: vi.fn(),
      setTheme: vi.fn(),
      toggleTheme: vi.fn(),
      updateSystemStatus: vi.fn(),
    });

    const { container } = render(<ServiceHealthMatrix />);

    // Online service should have green styling
    const onlineCard = container.querySelector('.bg-green-500\\/20');
    expect(onlineCard).toBeInTheDocument();

    // Offline service should have red styling
    const offlineCard = container.querySelector('.bg-red-500\\/20');
    expect(offlineCard).toBeInTheDocument();
  });
});
