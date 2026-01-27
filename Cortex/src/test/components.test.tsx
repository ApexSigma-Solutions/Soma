import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

describe('UI Components', () => {
  it('Input renders and has textbox role', () => {
    render(<Input placeholder="Test Input" />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('Button renders text', () => {
    render(<Button>Click Me</Button>);
    expect(screen.getByText('Click Me')).toBeInTheDocument();
  });
});
