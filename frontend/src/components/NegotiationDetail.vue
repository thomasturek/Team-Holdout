<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import type { Message, SessionDetail } from '@/api/types';
import { useDesk } from '@/stores/desk';
import LineChart, { type RefLine, type Series } from '@/components/charts/LineChart.vue';
import StatusPill from '@/components/StatusPill.vue';
import Avatar from '@/components/Avatar.vue';
import { COUNTRY_FLAG, TERM_LABELS, clock, duration, eur, eurCompact, humanize, pct, score100, shortName, termValue } from '@/format';

const props = defineProps<{ d: SessionDetail }>();
defineEmits<{ back: [] }>();

const desk = useDesk();
const router = useRouter();
const active = ref<string>('');
const expanded = ref<Set<number>>(new Set());

watch(
  () => props.d.key,
  () => {
    const dealId = props.d.result && props.d.threads.find((t) => t.name === props.d.deal_supplier)?.supplier_id;
    active.value = dealId || props.d.threads[0]?.supplier_id || '';
    expanded.value = new Set();
  },
  { immediate: true },
);

const thread = computed(() => props.d.threads.find((t) => t.supplier_id === active.value) ?? props.d.threads[0]);
const supplier = computed(() => (thread.value ? desk.supplierById.get(thread.value.supplier_id) : undefined));

const lastAsk = computed(() => {
  const asks = (thread.value?.prices ?? []).map((p) => p.ask).filter((x): x is number => x !== null);
  return asks.length ? asks[asks.length - 1] : null;
});
const firstAsk = computed(() => thread.value?.prices.find((p) => p.ask !== null)?.ask ?? null);
const finalPrice = computed(() => props.d.deal_price ?? lastAsk.value);
const priceDelta = computed(() => (finalPrice.value !== null && firstAsk.value ? (finalPrice.value - firstAsk.value) / firstAsk.value : null));
const saved = computed(() => (props.d.c_open !== null && props.d.c_deal !== null ? props.d.c_open - props.d.c_deal : null));

const chart = computed(() => {
  const pts = thread.value?.prices ?? [];
  const series: Series[] = [
    { name: 'Supplier ask', color: '#eb6834', values: pts.map((p) => p.ask), dots: true },
    { name: 'Our offer', color: '#2a78d6', values: pts.map((p) => p.offer), dots: true },
  ];
  const refs: RefLine[] = [];
  if (props.d.current_unit_price) refs.push({ y: props.d.current_unit_price, label: 'Current' });
  const alt = props.d.alternative?.terms?.unit_price;
  if (typeof alt === 'number') refs.push({ y: alt, label: 'Fallback' });
  return { series, refs, labels: pts.map((_, i) => (i === 0 ? 'Quote' : `Round ${i}`)) };
});

const terms = computed(() => {
  const src = props.d.result?.terms ?? lastSheet.value?.terms ?? {};
  return Object.entries(src).filter(([k]) => k in TERM_LABELS);
});

const lastSheet = computed(() => {
  const msgs = thread.value?.messages ?? [];
  for (let i = msgs.length - 1; i >= 0; i--) if (msgs[i].who === 'supplier' && msgs[i].sheets?.length) return msgs[i].sheets![0];
  return null;
});

const costs = computed(() => {
  const cb = props.d.result?.cost_breakdown ?? {};
  const rows = Object.entries(cb).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...rows.map(([, v]) => v));
  return rows.map(([k, v]) => ({ k: humanize(k), v, share: v / max }));
});

const mustHaves = computed(() =>
  props.d.must_haves.map((m) => {
    const actual = props.d.result?.terms?.[m.field];
    let ok: boolean | null = null;
    if (typeof actual === 'number' && typeof m.value === 'number') {
      ok = m.op === '<=' ? actual <= m.value : m.op === '>=' ? actual >= m.value : m.op === '<' ? actual < m.value : m.op === '>' ? actual > m.value : actual === m.value;
    }
    return { label: `${TERM_LABELS[m.field] ?? humanize(m.field)} ${m.op} ${termValue(m.field, m.value)}`, ok };
  }),
);

function sheetBits(terms: Record<string, unknown>) {
  const order = ['unit_price', ...props.d.negotiable.filter((k) => k !== 'unit_price')];
  return order.filter((k) => k in terms).slice(0, 4).map((k) => ({ k: TERM_LABELS[k] ?? humanize(k), v: termValue(k, terms[k]) }));
}

function verified(m: Message) {
  const c = m.claims ?? [];
  return { ok: c.filter((x) => x.result === 'verified').length, total: c.length };
}

function toggle(i: number) {
  const next = new Set(expanded.value);
  if (next.has(i)) next.delete(i);
  else next.add(i);
  expanded.value = next;
}
</script>

<template>
  <div class="detail-inner rise" :key="d.key">
    <div class="detail-head">
      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <button class="link-btn lg:hidden" @click="$emit('back')">‹ Back</button>
          <span class="eyebrow">{{ d.case_id.replace('case:', 'Case ') }} · {{ humanize(d.type) }} · {{ d.set }}</span>
        </div>
        <h1 class="detail-title">{{ d.title }}</h1>
        <div class="detail-tags">
          <span v-if="d.buyer_company" class="tag"><span class="material-symbols-rounded" style="font-size: 14px">domain</span>{{ d.buyer_company }}</span>
          <span class="tag">{{ d.suppliers.length }} supplier{{ d.suppliers.length > 1 ? 's' : '' }}</span>
          <span v-if="d.volume" class="tag">{{ d.volume.toLocaleString('en-GB') }} pcs / yr</span>
          <span class="tag mono">{{ d.session_id }}</span>
        </div>
      </div>
      <StatusPill :status="d.status" />
    </div>

    <div class="stats">
      <div class="card stat">
        <div class="eyebrow">Score</div>
        <div class="stat-value">{{ score100(d.score) }}<span class="text-sm font-semibold text-slate-400"> /100</span></div>
        <div class="meter mt-2"><span :style="{ width: (d.score ?? 0) * 100 + '%' }"></span></div>
      </div>
      <div class="card stat">
        <div class="eyebrow">Saved vs opening</div>
        <div class="stat-value">{{ saved !== null ? eurCompact(saved) : '–' }}</div>
        <div class="stat-foot">
          <template v-if="saved !== null && d.c_open"><span class="up">{{ pct(saved / d.c_open, 1) }}</span> of {{ eurCompact(d.c_open) }} total cost</template>
          <template v-else>{{ d.status === 'live' ? 'still negotiating' : 'no deal signed' }}</template>
        </div>
      </div>
      <div class="card stat">
        <div class="eyebrow">{{ d.deal_price !== null ? 'Deal price' : 'Latest ask' }}</div>
        <div class="stat-value">{{ eur(finalPrice, 2) }}</div>
        <div class="stat-foot">
          <template v-if="priceDelta !== null"><span :class="{ up: priceDelta < 0 }">{{ priceDelta <= 0 ? '−' : '+' }}{{ pct(Math.abs(priceDelta), 1) }}</span> vs quote {{ eur(firstAsk, 2) }}</template>
        </div>
      </div>
      <div class="card stat">
        <div class="eyebrow">Rounds</div>
        <div class="stat-value">{{ d.rounds }}<span v-if="d.round_limit" class="text-sm font-semibold text-slate-400"> / {{ d.round_limit }}</span></div>
        <div class="stat-foot">{{ d.messages }} e-mails · {{ duration(d.started_at, d.updated_at) }}</div>
      </div>
    </div>

    <div class="detail-grid">
      <div class="flex flex-col gap-3.5 min-w-0">
        <div class="card">
          <div class="card-head">
            <div>
              <h2 class="card-title">Price per unit</h2>
              <div class="card-sub">Supplier asks against our offers, round by round</div>
            </div>
            <div class="legend">
              <span><i style="background: #eb6834"></i>Supplier ask</span>
              <span><i style="background: #2a78d6"></i>Our offer</span>
            </div>
          </div>
          <div v-if="d.threads.length > 1" class="threads-tabs">
            <button v-for="t in d.threads" :key="t.supplier_id" class="thread-tab" :class="{ active: t.supplier_id === active }" @click="active = t.supplier_id">
              <Avatar :name="t.name" small />{{ shortName(t.name) }}
            </button>
          </div>
          <LineChart v-if="thread && thread.prices.length" :series="chart.series" :x-labels="chart.labels" :refs="chart.refs" :y-format="(v) => '€' + v.toFixed(2)" :height="230" />
        </div>

        <div class="card">
          <div class="card-head">
            <h2 class="card-title">Conversation</h2>
            <span class="card-sub">{{ thread?.messages.length ?? 0 }} messages with {{ thread ? shortName(thread.name) : '' }}</span>
          </div>
          <ol class="timeline">
            <li v-for="(m, i) in thread?.messages ?? []" :key="i" class="msg" :class="{ us: m.who === 'buyer' }">
              <span class="node">
                <Avatar v-if="m.who === 'supplier'" :name="thread!.name" />
                <Avatar v-else name="Us" us />
              </span>
              <div v-if="m.action" class="msg-action" :class="{ walk: m.action !== 'accept' }">
                <span class="material-symbols-rounded">{{ m.action === 'accept' ? 'task_alt' : 'logout' }}</span>
                {{ m.action === 'accept' ? `We accepted ${m.action_sheet ?? 'the offer'}` : 'We walked away' }}
                <span class="msg-when" style="font-weight: 400">{{ clock(m.t) }}</span>
              </div>
              <div v-else class="msg-card">
                <div class="msg-head">
                  <span class="msg-who">{{ m.who === 'buyer' ? 'Our team' : m.from_name || thread!.name }}</span>
                  <span v-if="m.status === 'final_offer'" class="pill warning"><span class="material-symbols-rounded">flag</span>Final offer</span>
                  <span v-else-if="m.status === 'agreed'" class="pill good"><span class="material-symbols-rounded">check_circle</span>Agreed</span>
                  <span v-if="verified(m).total" class="pill" :class="verified(m).ok === verified(m).total ? 'good' : 'warning'">
                    <span class="material-symbols-rounded">fact_check</span>{{ verified(m).ok }}/{{ verified(m).total }} facts confirmed
                  </span>
                  <span class="msg-when">
                    <template v-if="m.wait_s">replied in {{ Math.round(m.wait_s) }}s · </template>
                    <template v-if="m.decide_s">sent in {{ m.decide_s.toFixed(1) }}s · </template>
                    {{ clock(m.t) }}
                  </span>
                </div>
                <p v-if="m.body" class="msg-body" :class="{ clamp: !expanded.has(i) }" @click="toggle(i)">{{ m.body }}</p>
                <div v-if="m.sheets?.length || m.attachments?.length" class="msg-foot">
                  <span v-for="(s, k) in m.sheets" :key="k" class="sheet">
                    <span class="text-slate-400">{{ String.fromCharCode(65 + k) }}</span>
                    <template v-for="(b, j) in sheetBits(s.terms)" :key="j">
                      <span v-if="j" class="sep">|</span>
                      <span>{{ j === 0 ? '' : b.k + ' ' }}<b>{{ b.v }}</b></span>
                    </template>
                  </span>
                  <span v-for="a in m.attachments" :key="a" class="tag"><span class="material-symbols-rounded" style="font-size: 14px">attach_file</span>{{ a }}</span>
                </div>
              </div>
            </li>
          </ol>
        </div>
      </div>

      <aside class="side">
        <div class="card card-pad">
          <span class="eyebrow">{{ d.result ? 'Agreed terms' : 'Current terms on the table' }}</span>
          <dl class="facts">
            <template v-for="[k, v] in terms" :key="k">
              <dt>{{ TERM_LABELS[k] }}</dt>
              <dd>{{ termValue(k, v) }}</dd>
            </template>
          </dl>
          <p v-if="!terms.length" class="text-sm text-slate-400">No term sheet yet.</p>
        </div>

        <div v-if="costs.length" class="card card-pad">
          <span class="eyebrow">Total cost breakdown</span>
          <div class="bars">
            <div v-for="c in costs" :key="c.k" class="bar-row">
              <span class="truncate">{{ c.k }}</span>
              <div class="bar-track"><span :style="{ width: c.share * 100 + '%' }"></span></div>
              <span class="v">{{ eurCompact(c.v) }}</span>
            </div>
          </div>
          <dl class="facts mt-4 pt-3 border-t border-slate-100">
            <dt>Opening</dt><dd>{{ eur(d.c_open) }}</dd>
            <dt>Deal</dt><dd>{{ eur(d.c_deal) }}</dd>
            <dt>Fallback</dt><dd>{{ eur(d.c_alt) }}</dd>
            <dt>Best possible</dt><dd>{{ eur(d.c_best) }}</dd>
          </dl>
        </div>

        <div v-if="mustHaves.length" class="card card-pad">
          <span class="eyebrow">Must-haves</span>
          <div class="flex flex-col gap-2">
            <div v-for="m in mustHaves" :key="m.label" class="check" :class="{ bad: m.ok === false }">
              <span class="material-symbols-rounded">{{ m.ok === false ? 'cancel' : m.ok ? 'check_circle' : 'radio_button_unchecked' }}</span>
              {{ m.label }}
            </div>
          </div>
        </div>

        <div v-if="supplier" class="card card-pad">
          <span class="eyebrow">Supplier</span>
          <div class="flex items-center gap-3 mb-3 cursor-pointer" @click="router.push({ path: '/suppliers', query: { s: supplier.id } })">
            <Avatar :name="supplier.name" />
            <div class="min-w-0">
              <div class="text-sm font-semibold text-slate-900 truncate">{{ supplier.name }}</div>
              <div class="text-xs text-slate-400">{{ COUNTRY_FLAG[supplier.country ?? ''] ?? '' }} {{ supplier.country }} · {{ humanize(supplier.owner_type) }}</div>
            </div>
          </div>
          <dl class="facts">
            <dt>Profile</dt><dd>{{ humanize(supplier.archetype) }}</dd>
            <dt>Quality</dt>
            <dd><span class="qdot" :class="supplier.quality?.colour"></span>{{ supplier.quality?.ppm ?? '–' }} ppm</dd>
            <dt>On time</dt><dd>{{ supplier.quality?.otd_pct ?? '–' }}%</dd>
            <dt>Cash pressure</dt><dd>{{ pct(supplier.cash_pressure) }}</dd>
          </dl>
        </div>

        <div v-if="d.briefing" class="card card-pad">
          <span class="eyebrow">Brief</span>
          <p class="text-xs leading-relaxed text-slate-500 m-0">{{ d.briefing }}</p>
        </div>
      </aside>
    </div>
  </div>
</template>
