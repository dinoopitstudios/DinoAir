import { useCallback, useEffect, useMemo, useState } from 'react';

/**
 * Breakpoint thresholds matching common responsive design patterns
 */
export const BREAKPOINTS = {
  mobile: 768,
  tablet: 1024,
  desktop: 1280,
  wide: 1536,
} as const;

/**
 * Type for breakpoint names
 */
export type BreakpointName = keyof typeof BREAKPOINTS;

/**
 * Interface for the responsive hook return value
 */
export interface UseResponsiveReturn {
  /** Current window width */
  width: number;
  /** Current window height */
  height: number;
  /** True if screen width is less than mobile breakpoint (768px) */
  isMobile: boolean;
  /** True if screen width is between mobile and tablet breakpoints (768px - 1024px) */
  isTablet: boolean;
  /** True if screen width is between tablet and desktop breakpoints (1024px - 1280px) */
  isDesktop: boolean;
  /** True if screen width is greater than desktop breakpoint (1280px) */
  isWide: boolean;
  /** Check if current width is less than a specific breakpoint */
  isBelow: (breakpoint: BreakpointName | number) => boolean;
  /** Check if current width is greater than or equal to a specific breakpoint */
  isAbove: (breakpoint: BreakpointName | number) => boolean;
  /** Check if current width is between two breakpoints */
  isBetween: (min: BreakpointName | number, max: BreakpointName | number) => boolean;
  /** Get the current breakpoint name */
  breakpoint: 'mobile' | 'tablet' | 'desktop' | 'wide';
}

/**
 * Debounce function to limit resize event frequency
 */
function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: number | null = null;

  return (...args: Parameters<T>) => {
    if (timeout) {
      window.clearTimeout(timeout);
    }
    timeout = window.setTimeout(() => {
      func(...args);
    }, wait);
  };
}

/**
 * Custom hook for responsive design
 * Provides current viewport dimensions and breakpoint utilities
 *
 * @param debounceMs - Milliseconds to debounce resize events (default: 150)
 * @returns Object with viewport info and utility functions
 *
 * @example
 * ```tsx
 * const { isMobile, isTablet, isDesktop, width, isBelow } = useResponsive();
 *
 * if (isMobile) {
 *   return <MobileLayout />;
 * }
 *
 * if (isBelow('tablet')) {
 *   // Show compact view
 * }
 * ```
 */
export function useResponsive(debounceMs: number = 150): UseResponsiveReturn {
  // Initialize state with current window dimensions
  const [dimensions, setDimensions] = useState(() => {
    if (typeof window !== 'undefined') {
      return {
        width: window.innerWidth,
        height: window.innerHeight,
      };
    }
    // SSR fallback
    return {
      width: 1024,
      height: 768,
    };
  });

  // Handle window resize with debouncing
  const handleResize = useCallback(() => {
    setDimensions({
      width: window.innerWidth,
      height: window.innerHeight,
    });
  }, []);

  // Create debounced version of resize handler
  const debouncedResize = useMemo(
    () => debounce(handleResize, debounceMs),
    [handleResize, debounceMs]
  );

  // Set up resize event listener
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    // Add event listener
    window.addEventListener('resize', debouncedResize);

    // Call handler immediately to sync initial state
    handleResize();

    // Cleanup
    return () => {
      window.removeEventListener('resize', debouncedResize);
    };
  }, [debouncedResize, handleResize]);

  // Utility function to get numeric value from breakpoint name or number
  const getBreakpointValue = useCallback((breakpoint: BreakpointName | number): number => {
    if (typeof breakpoint === 'number') {
      return breakpoint;
    }
    return BREAKPOINTS[breakpoint];
  }, []);

  // Breakpoint check utilities
  const isBelow = useCallback(
    (breakpoint: BreakpointName | number): boolean => {
      return dimensions.width < getBreakpointValue(breakpoint);
    },
    [dimensions.width, getBreakpointValue]
  );

  const isAbove = useCallback(
    (breakpoint: BreakpointName | number): boolean => {
      return dimensions.width >= getBreakpointValue(breakpoint);
    },
    [dimensions.width, getBreakpointValue]
  );

  const isBetween = useCallback(
    (min: BreakpointName | number, max: BreakpointName | number): boolean => {
      const minValue = getBreakpointValue(min);
      const maxValue = getBreakpointValue(max);
      return dimensions.width >= minValue && dimensions.width < maxValue;
    },
    [dimensions.width, getBreakpointValue]
  );

  // Calculate current breakpoint
  const breakpoint = useMemo((): 'mobile' | 'tablet' | 'desktop' | 'wide' => {
    if (dimensions.width < BREAKPOINTS.mobile) {
      return 'mobile';
    }
    if (dimensions.width < BREAKPOINTS.tablet) {
      return 'tablet';
    }
    if (dimensions.width < BREAKPOINTS.desktop) {
      return 'desktop';
    }
    return 'wide';
  }, [dimensions.width]);

  // Calculate boolean flags for common breakpoints
  const isMobile = useMemo(() => dimensions.width < BREAKPOINTS.mobile, [dimensions.width]);
  const isTablet = useMemo(
    () => dimensions.width >= BREAKPOINTS.mobile && dimensions.width < BREAKPOINTS.tablet,
    [dimensions.width]
  );
  const isDesktop = useMemo(
    () => dimensions.width >= BREAKPOINTS.tablet && dimensions.width < BREAKPOINTS.desktop,
    [dimensions.width]
  );
  const isWide = useMemo(() => dimensions.width >= BREAKPOINTS.desktop, [dimensions.width]);

  return {
    width: dimensions.width,
    height: dimensions.height,
    isMobile,
    isTablet,
    isDesktop,
    isWide,
    isBelow,
    isAbove,
    isBetween,
    breakpoint,
  };
}

/**
 * Re-export for convenience
 */
export default useResponsive;
