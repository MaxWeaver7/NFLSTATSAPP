import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export type StatTrend = 'positive' | 'negative' | 'neutral';

/**
 * Consistent stat formatting for UI.
 *
 * - Integers (yards, attempts, TDs, etc.) should not show decimals.
 * - Rates/efficiency/advanced metrics should display as X.XX.
 */
export function formatStat(
  value: unknown,
  opts?: {
    decimals?: number;
    integer?: boolean;
    empty?: string;
  }
): string {
  const decimals = opts?.decimals ?? 2;
  const empty = opts?.empty ?? "—";
  if (value === null || value === undefined || value === "") return empty;

  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return empty;

  // Explicit integer formatting.
  if (opts?.integer) return String(Math.trunc(n));

  // If it is effectively an integer, show as integer (prevents 10.00 yards).
  if (Math.abs(n - Math.round(n)) < 1e-9) return String(Math.round(n));

  // Default: fixed decimals for advanced metrics.
  return n.toFixed(decimals);
}

export function getStatTrend(statName: string, value: number): StatTrend {
  const lowerStat = statName.toLowerCase();
  
  // Drop percentage - lower is better
  if (lowerStat.includes('drop')) {
    if (value < 5) return 'positive';
    if (value > 10) return 'negative';
    return 'neutral';
  }
  
  // Yards per catch - higher is better
  if (lowerStat.includes('ypc') || lowerStat.includes('yards per catch') || lowerStat.includes('avgyardspercat ch')) {
    if (value > 12) return 'positive';
    if (value < 8) return 'negative';
    return 'neutral';
  }
  
  // Yards per rush - higher is better
  if (lowerStat.includes('ypr') || lowerStat.includes('yards per rush') || lowerStat.includes('avgyardsperrush')) {
    if (value > 4.5) return 'positive';
    if (value < 3.5) return 'negative';
    return 'neutral';
  }
  
  // EPA - higher is better
  if (lowerStat.includes('epa')) {
    if (value > 0.1) return 'positive';
    if (value < -0.1) return 'negative';
    return 'neutral';
  }
  
  // YPRR (Yards Per Route Run) - higher is better
  if (lowerStat.includes('yprr')) {
    if (value > 2.0) return 'positive';
    if (value < 1.2) return 'negative';
    return 'neutral';
  }
  
  // Target Share - higher is better
  if (lowerStat.includes('target share') || lowerStat.includes('targetshare')) {
    if (value > 20) return 'positive';
    if (value < 10) return 'negative';
    return 'neutral';
  }
  
  // Snap % - higher is better
  if (lowerStat.includes('snap')) {
    if (value > 70) return 'positive';
    if (value < 50) return 'negative';
    return 'neutral';
  }
  
  // Catch Rate - higher is better
  if (lowerStat.includes('catch rate') || lowerStat.includes('catchrate')) {
    if (value > 70) return 'positive';
    if (value < 55) return 'negative';
    return 'neutral';
  }
  
  // YAC per reception - higher is better
  if (lowerStat.includes('yac')) {
    if (value > 5) return 'positive';
    if (value < 3) return 'negative';
    return 'neutral';
  }
  
  // ADOT (Average Depth of Target) - context dependent, but generally higher is good for deep threats
  if (lowerStat.includes('adot') || lowerStat.includes('depth')) {
    if (value > 12) return 'positive';
    if (value < 6) return 'negative';
    return 'neutral';
  }
  
  // Touchdowns - more is better
  if (lowerStat.includes('td') || lowerStat.includes('touchdown')) {
    if (value >= 5) return 'positive';
    if (value === 0) return 'negative';
    return 'neutral';
  }
  
  // General yards - more is better
  if (lowerStat.includes('yard')) {
    if (value > 800) return 'positive';
    if (value < 300) return 'negative';
    return 'neutral';
  }
  
  // Default to neutral
  return 'neutral';
}

/**
 * Ensures a hex color is readable on a dark background.
 * If the color's relative luminance is below a threshold, it gets lightened.
 */
export function ensureReadableColor(hex: string | undefined | null, minLuminance = 0.15): string {
  if (!hex) return '#ffffff';
  const h = hex.replace('#', '');
  if (h.length < 6) return hex;
  let r = parseInt(h.slice(0, 2), 16);
  let g = parseInt(h.slice(2, 4), 16);
  let b = parseInt(h.slice(4, 6), 16);

  // Relative luminance (sRGB)
  const lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;

  if (lum >= minLuminance) return hex;

  // Lighten by blending toward white until readable
  const factor = Math.max(0.35, minLuminance / Math.max(lum, 0.01));
  r = Math.min(255, Math.round(r + (255 - r) * factor));
  g = Math.min(255, Math.round(g + (255 - g) * factor));
  b = Math.min(255, Math.round(b + (255 - b) * factor));

  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

