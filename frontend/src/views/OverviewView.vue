<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useDesk } from '@/stores/desk';
import type { SessionStatus, SessionSummary } from '@/api/types';
import LineChart, { type Series } from '@/components/charts/LineChart.vue';
import StatusPill from '@/components/StatusPill.vue';
import Avatar from '@/components/Avatar.vue';
import { STATUS, ago, eurCompact, humanize, pct, score100, shortName } from '@/format';

const desk = useDesk();
const router = useRouter();

const all = computed(() => desk.visible);
const ended = computed(() => all.value.filter((s) => s.status !== 'live' && s.status !== 'stalled'));
const deals = computed(() => ended.value.filter((s) => s.status === 'deal'));
const scored = computed(() => ended.value.filter((s) => s.score !== null));

const avgScore = computed(() => (scored.value.length ? scored.value.reduce((a, s) => a + (s.score ?? 0), 0) / scored.value.length : null));
const dealRate = computed(() => (ended.value.length ? deals.value.length / ended.value.length : null));
const saved = computed(() => deals.value.reduce((a, s) => a + ((s.c_open ?? 0) - (s.c_deal ?? 0)), 0));
const savedPct = computed(() => {
  const open = deals.value.reduce((a, s) => a + (s.c_open ?? 0), 0);
  return open ? saved.value / open : null;
});
const today = computed(() => {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return all.value.filter((s) => s.started_at * 1000 >= d.getTime()).length;
});
const avgRounds = computed(() => (ended.value.length ? ended.value.reduce((a, s) => a + s.rounds, 0) / ended.value.length : 0));

const trend = computed(() => {
  const list = [...scored.value].sort((a, b) => a.updated_at - b.updated_at).slice(-120);
  const vals = list.map((s) => s.score as number);
  const roll = vals.map((_, i) => {
    const w = vals.slice(Math.max(0, i - 9), i + 1);
    return w.reduce((a, b) => a + b, 0) / w.length;
  });
  const labels = list.map((s) => new Date(s.updated_at * 1000).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }));
  const series: Series[] = [
    { name: 'Single run', color: '#c3cad6', values: vals, line: false, dots: true, label: false },
    { name: 'Rolling avg', color: '#2a78d6', values: roll },
  ];
  return { series, labels };
});

const OUTCOME_COLORS: Record<SessionStatus, string> = {
  deal: '#0f9d6b',
  no_deal: '#d6443c',
  walked: '#e0a100',
  timeout: '#c2410c',
  live: '#2a78d6',
  stalled: '#c3cad6',
};

const outcomes = computed(() => {
  const order: SessionStatus[] = ['deal', 'live', 'walked', 'no_deal', 'timeout', 'stalled'];
  const total = all.value.length || 1;
  return order
    .map((k) => ({ k, n: all.value.filter((s) => s.status === k).length }))
    .filter((o) => o.n > 0)
    .map((o) => ({ ...o, share: o.n / total, color: OUTCOME_COLORS[o.k], label: STATUS[o.k].label }));
});

interface CaseRow {
  case_id: string;
  title: string;
  type: string | null;
  suppliers: string[];
  runs: number;
  dealRate: number | null;
  avg: number | null;
  best: number | null;
  saved: number;
  last: SessionSummary;
}

const cases = computed<CaseRow[]>(() => {
  const by = new Map<string, SessionSummary[]>();
  for (const s of all.value) by.set(s.case_id, [...(by.get(s.case_id) ?? []), s]);
  return [...by.entries()]
    .map(([case_id, list]) => {
      const done = list.filter((s) => s.status !== 'live' && s.status !== 'stalled');
      const sc = done.map((s) => s.score).filter((x): x is number => x !== null);
      const dl = done.filter((s) => s.status === 'deal');
      return {
        case_id,
        title: list[0].title,
        type: list[0].type,
        suppliers: list[0].suppliers.map((x) => x.name),
        runs: list.length,
        dealRate: done.length ? dl.length / done.length : null,
        avg: sc.length ? sc.reduce((a, b) => a + b, 0) / sc.length : null,
        best: sc.length ? Math.max(...sc) : null,
        saved: dl.length ? dl.reduce((a, s) => a + ((s.c_open ?? 0) - (s.c_deal ?? 0)), 0) / dl.length : 0,
        last: list[0],
      };
    })
    .sort((a, b) => a.case_id.localeCompare(b.case_id));
});

const feed = computed(() => all.value.slice(0, 9));

function feedTitle(s: SessionSummary) {
  if (s.status === 'deal') return `Deal with ${shortName(s.deal_supplier ?? s.suppliers[0]?.name ?? '')}`;
  if (s.status === 'live') return `Negotiating with ${s.suppliers.map((x) => shortName(x.name)).join(', ')}`;
  return `${STATUS[s.status].label} · ${s.suppliers.map((x) => shortName(x.name)).join(', ')}`;
}

function open(key: string) {
  router.push(`/negotiations/${key}`);
}

function openCase(row: CaseRow) {
  router.push({ path: `/negotiations/${row.last.key}`, query: { case: row.case_id } });
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Overview</h1>
        <p class="page-sub">Every supplier negotiation, its outcome and what it saved.</p>
      </div>
      <button class="btn" @click="router.push('/negotiations')"><span class="material-symbols-rounded">forum</span>Open negotiations</button>
    </div>

    <p v-if="desk.error" class="error-bar">{{ desk.error }}</p>

    <div class="kpis">
      <div class="card kpi rise">
        <div class="kpi-label"><span class="material-symbols-rounded">forum</span>Negotiations</div>
        <div class="kpi-value">{{ all.length }}</div>
        <div class="kpi-foot"><b>{{ today }}</b> started today</div>
      </div>
      <div class="card kpi rise" style="animation-delay: 40ms">
        <div class="kpi-label"><span class="material-symbols-rounded">handshake</span>Deal rate</div>
        <div class="kpi-value">{{ pct(dealRate) }}</div>
        <div class="kpi-foot"><b>{{ deals.length }}</b> of {{ ended.length }} closed with a deal</div>
      </div>
      <div class="card kpi rise" style="animation-delay: 80ms">
        <div class="kpi-label"><span class="material-symbols-rounded">speed</span>Avg score</div>
        <div class="kpi-value">{{ score100(avgScore) }}<span class="text-base font-semibold text-slate-400"> /100</span></div>
        <div class="kpi-foot">share of the best possible saving</div>
      </div>
      <div class="card kpi rise" style="animation-delay: 120ms">
        <div class="kpi-label"><span class="material-symbols-rounded">savings</span>Saved vs opening</div>
        <div class="kpi-value">{{ eurCompact(saved) }}</div>
        <div class="kpi-foot"><b>{{ pct(savedPct, 1) }}</b> off the suppliers' opening total cost</div>
      </div>
      <div class="card kpi rise" style="animation-delay: 160ms">
        <div class="kpi-label"><span class="material-symbols-rounded">sync_alt</span>Avg rounds</div>
        <div class="kpi-value">{{ avgRounds.toFixed(1) }}</div>
        <div class="kpi-foot"><b>{{ desk.liveCount }}</b> running right now</div>
      </div>
    </div>

    <div class="grid-2-1">
      <div class="card rise" style="animation-delay: 120ms">
        <div class="card-head">
          <div>
            <h2 class="card-title">Score over time</h2>
            <div class="card-sub">Last {{ trend.series[0].values.length }} finished negotiations, 0–100</div>
          </div>
          <div class="legend">
            <span><i style="background: #c3cad6; height: 8px; width: 8px; border-radius: 50%"></i>Single run</span>
            <span><i style="background: #2a78d6"></i>Rolling avg (10)</span>
          </div>
        </div>
        <LineChart v-if="trend.labels.length" :series="trend.series" :x-labels="trend.labels" :y-min="0" :y-max="1" :y-format="(v) => Math.round(v * 100).toString()" :height="240" />
        <div v-else class="empty">No finished negotiations yet.</div>
      </div>

      <div class="card rise" style="animation-delay: 160ms">
        <div class="card-head">
          <h2 class="card-title">Outcomes</h2>
          <span class="card-sub">{{ all.length }} total</span>
        </div>
        <div class="outcomes">
          <div class="outcome-bar">
            <span v-for="o in outcomes" :key="o.k" :style="{ width: o.share * 100 + '%', background: o.color }" :title="`${o.label}: ${o.n}`"></span>
          </div>
          <div v-for="o in outcomes" :key="'r' + o.k" class="outcome-row">
            <StatusPill :status="o.k" />
            <span><b>{{ o.n }}</b> <span class="text-slate-400">· {{ pct(o.share) }}</span></span>
          </div>
        </div>
      </div>
    </div>

    <div class="grid-2-1">
      <div class="card rise" style="animation-delay: 200ms; overflow: hidden">
        <div class="card-head" style="padding-bottom: 0.85rem">
          <h2 class="card-title">Cases</h2>
          <span class="card-sub">{{ cases.length }} cases</span>
        </div>
        <table class="table">
          <thead>
            <tr>
              <th>Case</th>
              <th>Type</th>
              <th class="num">Runs</th>
              <th class="num">Deal rate</th>
              <th class="num">Avg saved</th>
              <th class="num">Avg score</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in cases" :key="c.case_id" @click="openCase(c)">
              <td>
                <div class="flex items-center gap-3">
                  <Avatar :name="c.suppliers[0] ?? c.title" small />
                  <div class="min-w-0">
                    <div class="strong truncate" style="max-width: 280px">{{ c.title }}</div>
                    <div class="text-xs text-slate-400">{{ c.case_id.replace('case:', '') }} · {{ c.suppliers.length > 1 ? `${c.suppliers.length} suppliers` : shortName(c.suppliers[0] ?? '') }}</div>
                  </div>
                </div>
              </td>
              <td><span class="tag">{{ humanize(c.type) }}</span></td>
              <td class="num">{{ c.runs }}</td>
              <td class="num">{{ pct(c.dealRate) }}</td>
              <td class="num">{{ eurCompact(c.saved) }}</td>
              <td class="num">
                <div class="score-cell">
                  <div class="meter"><span :style="{ width: (c.avg ?? 0) * 100 + '%' }"></span></div>
                  <span class="strong" style="min-width: 22px">{{ score100(c.avg) }}</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card rise" style="animation-delay: 240ms">
        <div class="card-head">
          <h2 class="card-title">Activity</h2>
          <span class="card-sub">updates every few seconds</span>
        </div>
        <ul class="feed">
          <li v-for="s in feed" :key="s.key" @click="open(s.key)">
            <Avatar :name="s.deal_supplier ?? s.suppliers[0]?.name ?? s.title" small />
            <div class="feed-main">
              <div class="feed-title">{{ feedTitle(s) }}</div>
              <div class="feed-sub">
                {{ s.title }}<template v-if="s.score !== null"> · score {{ score100(s.score) }}</template>
              </div>
            </div>
            <span class="feed-when">{{ ago(s.updated_at) }}</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
