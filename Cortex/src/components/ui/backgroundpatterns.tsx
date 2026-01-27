import React from 'react';
import { useSystemStore } from '@/lib/store/systemStore';

// We import these as URLs to use in background-image styles
// Note: Ensure your vite.config.ts handles SVG assets correctly (default usually works)
// You might need to adjust paths based on where you actually drop the files.
import geometricDark from '@/assets/Patterns/Dark/pattern-geometric-dark.svg';
import circuitDark from '@/assets/Patterns/Dark/pattern-circuitflow-dark.svg';
import waveDark from '@/assets/Patterns/Dark/pattern-gradientwave-dark.svg';
import gridDark from '@/assets/Patterns/Dark/pattern-apexgrid-dark.svg';

import geometricLight from '@/assets/Patterns/Light/pattern-geometric-light.svg';
import circuitLight from '@/assets/Patterns/Light/pattern-circuitflow-light.svg';
import waveLight from '@/assets/Patterns/Light/pattern-gradientwave-light.svg';
import gridLight from '@/assets/Patterns/Light/pattern-apexgrid-light.svg';

export type PatternType = 'geometric' | 'circuit' | 'wave' | 'grid' | 'none';

interface BackgroundPatternsProps {
  opacity?: number;
  className?: string;
  pattern?: PatternType; // Optional override
}

export const BackgroundPatterns: React.FC<BackgroundPatternsProps> = ({ 
  opacity = 0.05, 
  className,
  pattern = 'circuit' // Default pattern
}) => {
  // Get theme from systemStore for proper reactivity
  const { theme } = useSystemStore();
  const isLightMode = theme === 'light';

  // Debug logging
  React.useEffect(() => {
    console.log('[BackgroundPatterns] Pattern changed:', pattern);
    console.log('[BackgroundPatterns] Opacity:', opacity);
    console.log('[BackgroundPatterns] Theme:', theme);
    console.log('[BackgroundPatterns] Sample import (circuitDark):', circuitDark);
  }, [pattern, opacity, theme]);

  const getPatternUrl = (type: PatternType, light: boolean) => {
    switch (type) {
      case 'geometric': return light ? geometricLight : geometricDark;
      case 'circuit': return light ? circuitLight : circuitDark;
      case 'wave': return light ? waveLight : waveDark;
      case 'grid': return light ? gridLight : gridDark;
      default: return '';
    }
  };

  const patternUrl = getPatternUrl(pattern, isLightMode);

  // Debug logging
  React.useEffect(() => {
    console.log('[BackgroundPatterns] Pattern:', pattern, '| Opacity:', opacity, '| Theme:', theme);
    console.log('[BackgroundPatterns] Pattern URL:', patternUrl);
  }, [pattern, opacity, theme, patternUrl]);

  if (pattern === 'none' || !patternUrl) return null;

  return (
    <div 
      className={`fixed inset-0 pointer-events-none z-0${className ? ` ${className}` : ''}`}
      style={{
        backgroundImage: `url("${patternUrl}")`, // ✅ Fixed: Added quotes around the data URL
        backgroundRepeat: 'repeat',
        backgroundSize: '200px 200px',
        opacity: opacity,
      }}
    />
  );
};