import fs from 'node:fs';
import path from 'node:path';
import type { Plugin } from 'vite';

type Json = Record<string, any>;

const LIVE_WINDOW_S = 15 * 60;

interface Parsed {
  mtime: number;
  summary: Json;
  detail: Json;
}

const cache = new Map<string, Parsed>();
let profileCache: { mtime: number; data: Json } | null = null;

function readJsonl(file: string): Json[] {
  const out: Json[] = [];
  for (const line of fs.readFileSync(file, 'utf-8').split('\n')) {
    if (!line.trim()) continue;
    try {
      out.push(JSON.parse(line));
    } catch {
      continue;
    }
  }
  return out;
}

function loadProfiles(runsDir: string): Json {
  const file = path.join(runsDir, 'profiles', 'all.json');
  if (!fs.existsSync(file)) return {};
  const mtime = fs.statSync(file).mtimeMs;
  if (profileCache && profileCache.mtime === mtime) return profileCache.data;
  const raw = JSON.parse(fs.readFileSync(file, 'utf-8'));
  profileCache = { mtime, data: raw.profiles ?? {} };
  return profileCache.data;
}

function supplierName(profiles: Json, id: string, fromName?: string): string {
  const parts = profiles[id];
  const first = parts ? (Object.values(parts)[0] as Json) : null;
  if (first?.name) return first.name;
  if (fromName && fromName.includes(', ')) return fromName.split(', ').slice(1).join(', ');
  return fromName || id;
}

function firstPrice(sheets: Json[] | null | undefined): number | null {
  const p = sheets?.[0]?.terms?.unit_price;
  return typeof p === 'number' ? p : null;
}

function sheetList(sheets: Json[] | null | undefined): Json[] {
  return (sheets ?? []).map((s) => ({ id: s.term_sheet_id ?? null, terms: s.terms ?? {} }));
}

function parseSession(file: string, set: string, profiles: Json, mtime: number): Parsed | null {
  const events = readJsonl(file);
  const head = events.find((e) => e.kind === 'case');
  if (!head) return null;
  const c: Json = head.case ?? {};
  const threads = new Map<string, Json>();
  const thread = (id: string) => {
    if (!threads.has(id)) threads.set(id, { supplier_id: id, name: supplierName(profiles, id), status: 'open', messages: [], prices: [] });
    return threads.get(id)!;
  };
  for (const id of c.suppliers ?? []) thread(id);

  let result: Json | null = null;
  let endReason: string | null = null;
  let rounds = 0;
  let lastT = head.t;

  for (const e of events) {
    lastT = Math.max(lastT, e.t ?? 0);
    if (e.kind === 'opening') {
      for (const [sid, msgs] of Object.entries<Json[]>(e.threads ?? {})) {
        const th = thread(sid);
        for (const m of msgs) {
          th.name = supplierName(profiles, sid, m.from_name);
          th.messages.push({ who: 'supplier', t: e.t, from_name: m.from_name, subject: m.subject, body: m.body, status: m.status, sheets: sheetList(m.term_sheets), claims: m.claim_results ?? [], attachments: (m.attachments ?? []).map((a: Json) => a.name) });
          th.status = m.status ?? th.status;
          th.prices.push({ round: 0, ask: firstPrice(m.term_sheets), offer: null });
        }
      }
    } else if (e.kind === 'sent') {
      const th = thread(e.supplier_id);
      const m = e.message ?? {};
      th.messages.push({ who: 'buyer', t: e.t, subject: m.subject, body: m.body, sheets: sheetList(m.term_sheets), decide_s: e.decide_s ?? null });
      const round = th.prices.length;
      th.prices.push({ round, ask: null, offer: firstPrice(m.term_sheets) });
    } else if (e.kind === 'reply') {
      const th = thread(e.supplier_id);
      const m = e.message ?? {};
      th.messages.push({ who: 'supplier', t: e.t, from_name: m.from_name, subject: m.subject, body: m.body, status: m.status, sheets: sheetList(m.term_sheets), claims: m.claim_results ?? [], attachments: (m.attachments ?? []).map((a: Json) => a.name), wait_s: e.wait_s ?? null });
      th.status = m.status ?? th.status;
      const last = th.prices[th.prices.length - 1];
      if (last && last.ask === null) last.ask = firstPrice(m.term_sheets);
      else th.prices.push({ round: th.prices.length, ask: firstPrice(m.term_sheets), offer: null });
      rounds = Math.max(rounds, th.messages.filter((x: Json) => x.who === 'buyer').length);
    } else if (e.kind === 'closing') {
      const th = thread(e.supplier_id);
      const a = e.message?.action ?? {};
      th.messages.push({ who: 'buyer', t: e.t, action: a.type ?? 'close', action_sheet: a.term_sheet_id ?? null });
    } else if (e.kind === 'drop') {
      thread(e.supplier_id).status = 'dropped';
    } else if (e.kind === 'result') {
      result = e.result ?? null;
    } else if (e.kind === 'session') {
      endReason = e.data?.end_reason ?? endReason;
      rounds = Math.max(rounds, e.data?.rounds ?? 0);
    } else if (e.kind === 'closed') {
      endReason = e.end_reason ?? endReason;
    }
  }

  const now = Date.now() / 1000;
  let status: string;
  if (result?.deal) status = 'deal';
  else if (result) status = endReason === 'walked_away' ? 'walked' : endReason === 'timeout' ? 'timeout' : 'no_deal';
  else status = now - mtime / 1000 < LIVE_WINDOW_S ? 'live' : 'stalled';

  const dealThread = result?.supplier_id ? threads.get(result.supplier_id) : null;
  const openingPrices = [...threads.values()].map((t) => t.prices[0]?.ask).filter((x): x is number => typeof x === 'number');
  const messageCount = [...threads.values()].reduce((n, t) => n + t.messages.length, 0);

  const summary = {
    key: `${set}/${head.session_id}`,
    session_id: head.session_id,
    set,
    case_id: head.case_id ?? c.case_id,
    title: c.title ?? head.case_id,
    type: c.type ?? null,
    buyer_company: (c.briefing ?? '').match(/negotiate for (.+?) with/)?.[1] ?? null,
    suppliers: [...threads.values()].map((t) => ({ id: t.supplier_id, name: t.name, status: t.status })),
    status,
    end_reason: endReason,
    score: typeof result?.score === 'number' ? result.score : null,
    c_open: result?.c_open ?? null,
    c_deal: result?.c_deal ?? null,
    c_alt: result?.c_alt ?? null,
    c_best: result?.c_best ?? null,
    deal_supplier: dealThread ? dealThread.name : null,
    deal_price: result?.terms?.unit_price ?? null,
    opening_price: openingPrices.length ? Math.min(...openingPrices) : null,
    volume: c.buyer?.need_per_year ?? c.fixed_terms?.volume_per_year ?? null,
    rounds,
    messages: messageCount,
    started_at: head.t,
    updated_at: lastT,
    purpose: head.run?.purpose ?? head.run?.agent ?? null,
  };

  const detail = {
    ...summary,
    briefing: c.briefing ?? null,
    negotiable: c.negotiable ?? [],
    fixed_terms: c.fixed_terms ?? {},
    round_limit: c.round_limit ?? null,
    must_haves: c.buyer?.must_haves ?? [],
    alternative: c.buyer?.alternative ?? null,
    current_unit_price: c.buyer?.current_unit_price ?? null,
    result: result ? { terms: result.terms ?? {}, cost_breakdown: result.cost_breakdown ?? {}, must_haves_ok: result.must_haves_ok ?? null } : null,
    threads: [...threads.values()],
  };
  return { mtime, summary, detail };
}

function sessionFiles(runsDir: string): { file: string; set: string }[] {
  const out: { file: string; set: string }[] = [];
  if (!fs.existsSync(runsDir)) return out;
  for (const set of fs.readdirSync(runsDir)) {
    const setDir = path.join(runsDir, set);
    if (!fs.statSync(setDir).isDirectory()) continue;
    for (const caseDir of fs.readdirSync(setDir)) {
      if (!caseDir.startsWith('case_')) continue;
      const dir = path.join(setDir, caseDir);
      if (!fs.statSync(dir).isDirectory()) continue;
      for (const f of fs.readdirSync(dir)) if (f.endsWith('.jsonl')) out.push({ file: path.join(dir, f), set });
    }
  }
  return out;
}

function allSessions(runsDir: string): Parsed[] {
  const profiles = loadProfiles(runsDir);
  const out: Parsed[] = [];
  for (const { file, set } of sessionFiles(runsDir)) {
    const mtime = fs.statSync(file).mtimeMs;
    let p = cache.get(file);
    if (!p || p.mtime !== mtime) {
      const parsed = parseSession(file, set, profiles, mtime);
      if (!parsed) continue;
      cache.set(file, parsed);
      p = parsed;
    }
    out.push(p);
  }
  return out.sort((a, b) => b.summary.updated_at - a.summary.updated_at);
}

function suppliers(runsDir: string): Json[] {
  const profiles = loadProfiles(runsDir);
  return Object.entries<Json>(profiles).map(([id, parts]) => {
    const list = Object.values<Json>(parts);
    const p = list[0] ?? {};
    return {
      id,
      name: p.name ?? id,
      country: p.country ?? null,
      owner_type: p.owner_type ?? null,
      archetype: p.archetype ?? null,
      approval_style: p.approval_style ?? null,
      cash_pressure: p.cash_pressure ?? 0,
      cash_reasons: p.cash_reasons ?? [],
      quality: p.quality ?? null,
      vendor_terms: p.vendor_terms ?? null,
      parts: list.map((x) => ({ part_id: x.part_id, floor: x.floor_estimate ?? null, best_price: x.memory?.best_price ?? null, deal_price: x.memory?.deal_price ?? null, opening_price: x.memory?.opening_price ?? null })),
      notes: p.notes ?? [],
      claims: (p.claims ?? []).map((c: Json) => c.sentence),
    };
  });
}

function send(res: any, status: number, body: unknown) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify(body));
}

export function runsApi(runsDir: string): Plugin {
  return {
    name: 'runs-api',
    configureServer(server) {
      server.middlewares.use('/api', (req, res) => {
        try {
          const url = new URL(req.url ?? '/', 'http://local');
          const parts = url.pathname.split('/').filter(Boolean);
          if (parts[0] === 'sessions' && parts.length === 1) {
            return send(res, 200, allSessions(runsDir).map((p) => p.summary));
          }
          if (parts[0] === 'sessions' && parts.length === 3) {
            const key = `${parts[1]}/${parts[2]}`;
            const hit = allSessions(runsDir).find((p) => p.summary.key === key);
            return hit ? send(res, 200, hit.detail) : send(res, 404, { detail: 'session not found' });
          }
          if (parts[0] === 'suppliers') return send(res, 200, suppliers(runsDir));
          return send(res, 404, { detail: 'not found' });
        } catch (err) {
          return send(res, 500, { detail: String(err) });
        }
      });
    },
  };
}
