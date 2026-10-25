import type { SessionStatus } from '@/api/types';

const eur0 = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });
const eur2 = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function eur(v: number | null | undefined, digits: 0 | 2 = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '–';
  return (digits === 2 ? eur2 : eur0).format(v);
}

export function eurCompact(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '–';
  const a = Math.abs(v);
  const sign = v < 0 ? '−' : '';
  if (a >= 1e6) return `${sign}€${(a / 1e6).toFixed(2)}M`;
  if (a >= 1e3) return `${sign}€${(a / 1e3).toFixed(1)}k`;
  return `${sign}€${a.toFixed(0)}`;
}

export function score100(v: number | null | undefined): string {
  if (v === null || v === undefined) return '–';
  return Math.round(v * 100).toString();
}

export function pct(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '–';
  return `${(v * 100).toFixed(digits)}%`;
}

export function ago(t: number | null | undefined): string {
  if (!t) return '';
  const s = Math.max(0, Date.now() / 1000 - t);
  if (s < 45) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return `${Math.round(s / 86400)}d ago`;
}

export function clock(t: number | null | undefined): string {
  if (!t) return '';
  return new Date(t * 1000).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

export function duration(a: number, b: number): string {
  const s = Math.max(0, Math.round(b - a));
  const m = Math.floor(s / 60);
  return m ? `${m}m ${String(s % 60).padStart(2, '0')}s` : `${s}s`;
}

export function initials(name: string): string {
  const words = name.replace(/[^\p{L}\s]/gu, ' ').split(/\s+/).filter((w) => w.length > 1 && w[0] === w[0].toUpperCase());
  return (words.slice(0, 2).map((w) => w[0]).join('') || name.slice(0, 2)).toUpperCase();
}

export function shortName(name: string): string {
  return name.replace(/\s+(GmbH & Co\. KG|GmbH|Sp\. z o\.o\.|s\.r\.o\.|S\.p\.A\.|S\.r\.l\.|AG|KG|Ltd\.?|SAS|S\.A\.|a\.s\.|Kft\.)\.?$/i, '').trim();
}

export function humanize(s: string | null | undefined): string {
  if (!s) return '–';
  return s.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}

export const STATUS: Record<SessionStatus, { label: string; tone: string; icon: string }> = {
  live: { label: 'Live', tone: 'live', icon: 'radio_button_checked' },
  deal: { label: 'Deal', tone: 'good', icon: 'check_circle' },
  no_deal: { label: 'No deal', tone: 'critical', icon: 'cancel' },
  walked: { label: 'Walked away', tone: 'warning', icon: 'logout' },
  timeout: { label: 'Timed out', tone: 'serious', icon: 'timer_off' },
  stalled: { label: 'Stalled', tone: 'muted', icon: 'pause_circle' },
};

export const TERM_LABELS: Record<string, string> = {
  unit_price: 'Unit price',
  payment_days: 'Payment',
  lead_time_days: 'Lead time',
  volume_per_year: 'Volume / yr',
  contract_months: 'Contract',
  effective_date: 'Effective',
  index_clause: 'Index clause',
  incoterm: 'Incoterm',
  tooling_eur: 'Tooling',
  ppm_commitment: 'PPM',
  chargeback_eur_per_complaint: 'Chargeback',
};

export function termValue(key: string, v: unknown): string {
  if (v === null || v === undefined || v === '') return '–';
  if (typeof v === 'number') {
    if (key === 'unit_price') return eur(v, 2);
    if (key === 'tooling_eur' || key === 'chargeback_eur_per_complaint') return eur(v);
    if (key.endsWith('_days')) return `${v} d`;
    if (key === 'contract_months') return `${v} mo`;
    if (key === 'volume_per_year') return v.toLocaleString('en-GB');
    return v.toLocaleString('en-GB');
  }
  if (typeof v === 'object') return Object.entries(v as Record<string, unknown>).map(([k, x]) => `${k} ${x}`).join(', ');
  return String(v);
}

export const COUNTRY_FLAG: Record<string, string> = {
  DE: '🇩🇪', PL: '🇵🇱', CZ: '🇨🇿', IT: '🇮🇹', AT: '🇦🇹', SK: '🇸🇰', HU: '🇭🇺', FR: '🇫🇷', NL: '🇳🇱', CH: '🇨🇭', ES: '🇪🇸', SI: '🇸🇮', RO: '🇷🇴', TR: '🇹🇷', CN: '🇨🇳', IN: '🇮🇳', PT: '🇵🇹', BE: '🇧🇪', DK: '🇩🇰', SE: '🇸🇪',
};
