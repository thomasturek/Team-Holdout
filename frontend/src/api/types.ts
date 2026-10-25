export type SessionStatus = 'live' | 'deal' | 'no_deal' | 'walked' | 'timeout' | 'stalled';

export interface SupplierRef {
  id: string;
  name: string;
  status: string;
}

export interface SessionSummary {
  key: string;
  session_id: string;
  set: string;
  case_id: string;
  title: string;
  type: string | null;
  buyer_company: string | null;
  suppliers: SupplierRef[];
  status: SessionStatus;
  end_reason: string | null;
  score: number | null;
  c_open: number | null;
  c_deal: number | null;
  c_alt: number | null;
  c_best: number | null;
  deal_supplier: string | null;
  deal_price: number | null;
  opening_price: number | null;
  volume: number | null;
  rounds: number;
  messages: number;
  started_at: number;
  updated_at: number;
  purpose: string | null;
}

export interface TermSheet {
  id: string | null;
  terms: Record<string, unknown>;
}

export interface Message {
  who: 'supplier' | 'buyer';
  t: number;
  from_name?: string;
  subject?: string;
  body?: string;
  status?: string;
  sheets?: TermSheet[];
  claims?: { index: number; result: string }[];
  attachments?: string[];
  wait_s?: number | null;
  decide_s?: number | null;
  action?: string;
  action_sheet?: string | null;
}

export interface PricePoint {
  round: number;
  ask: number | null;
  offer: number | null;
}

export interface Thread {
  supplier_id: string;
  name: string;
  status: string;
  messages: Message[];
  prices: PricePoint[];
}

export interface SessionDetail extends SessionSummary {
  briefing: string | null;
  negotiable: string[];
  fixed_terms: Record<string, unknown>;
  round_limit: number | null;
  must_haves: { field: string; op: string; value: unknown }[];
  alternative: { kind: string; ref: string; terms: Record<string, unknown> } | null;
  current_unit_price: number | null;
  result: { terms: Record<string, unknown>; cost_breakdown: Record<string, number>; must_haves_ok: boolean | null } | null;
  threads: Thread[];
}

export interface Supplier {
  id: string;
  name: string;
  country: string | null;
  owner_type: string | null;
  archetype: string | null;
  approval_style: string | null;
  cash_pressure: number;
  cash_reasons: string[];
  quality: { otd_pct?: number; ppm?: number; colour?: string; quarter?: string } | null;
  vendor_terms: Record<string, unknown> | null;
  parts: { part_id: string; floor: number | null; best_price: number | null; deal_price: number | null; opening_price: number | null }[];
  notes: string[];
  claims: string[];
}
