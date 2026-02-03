import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ManualIngestForm } from '@/components/ingress/ManualIngestForm';
import { useToastStore } from '@/lib/store/useToastStore';

vi.mock('@/lib/api/ingressApi');
vi.mock('@/lib/store/useToastStore');

describe('ManualIngestForm', () => {
  const mockAddToast = vi.fn();

  beforeEach(() => {
    vi.mocked(useToastStore).mockReturnValue({
      addToast: mockAddToast,
      toasts: [],
      removeToast: vi.fn(),
    });
  });

  it('should render form elements correctly', () => {
    render(<ManualIngestForm />);

    expect(screen.getByPlaceholderText('e.g., manual, test, webhook')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('e.g., user_action, system_event')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('{"key": "value"}')).toBeInTheDocument();
    expect(screen.getByText('Capture Signal')).toBeInTheDocument();
  });

  it('should show error for invalid JSON', async () => {
    render(<ManualIngestForm />);

    const payloadInput = screen.getByPlaceholderText('{"key": "value"}');
    fireEvent.change(payloadInput, { target: { value: 'invalid json' } });

    const submitButton = screen.getByText('Capture Signal');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockAddToast).toHaveBeenCalledWith('Invalid JSON payload format', 'error');
    });
  });

  it('should format JSON when format button clicked', () => {
    render(<ManualIngestForm />);

    const payloadInput = screen.getByPlaceholderText('{"key": "value"}');
    fireEvent.change(payloadInput, { target: { value: '{"key":"value"}' } });

    const formatButton = screen.getByText('Format JSON');
    fireEvent.click(formatButton);

    expect(payloadInput).toHaveValue('{\n  "key": "value"\n}');
  });
});
