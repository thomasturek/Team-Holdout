<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDesk } from '@/stores/desk';
import type { Supplier } from '@/api/types';
import Avatar from '@/components/Avatar.vue';
import { COUNTRY_FLAG, eur, humanize, pct, score100, shortName } from '@/format';

const desk = useDesk();
const route = useRoute();
const router = useRouter();

const q = ref('');
const sort = ref<'name' | 'score' | 'runs' | 'cash'>('runs');

const stats = computed(() => {
  const m = new Map<string, { runs: number; deals: number; scores: number[]; last: number }>();
  for (const s of desk.visible) {
    for (const sup of s.suppliers) {
      const e = m.get(sup.id) ?? { runs: 0, deals: 0, scores: [], last: 0 };
      e.runs += 1;
      if (s.status === 'deal' && s.deal_supplier === sup.name) {
        e.deals += 1;
        if (s.score !== null) e.scores.push(s.score);
      }
      e.last = Math.max(e.last, s.updated_at);
      m.set(sup.id, e);
    }
  }
  return m;
});

const rows = computed(() => {
  const needle = q.value.trim().toLowerCase();
  const list = desk.suppliers
    .filter((s) => !needle || [s.name, s.country, s.archetype, s.id].join(' ').toLowerCase().includes(needle))
    .map((s) => {
      const st = stats.value.get(s.id);
      const avg = st?.scores.length ? st.scores.reduce((a, b) => a + b, 0) / st.scores.length : null;
      return { s, runs: st?.runs ?? 0, deals: st?.deals ?? 0, avg };
    });
  const by = {
    name: (a: (typeof list)[number], b: (typeof list)[number]) => a.s.name.localeCompare(b.s.name),
    score: (a: (typeof list)[number], b: (typeof list)[number]) => (b.avg ?? -1) - (a.avg ?? -1),
    runs: (a: (typeof list)[number], b: (typeof list)[number]) => b.runs - a.runs || a.s.name.localeCompare(b.s.name),
    cash: (a: (typeof list)[number], b: (typeof list)[number]) => b.s.cash_pressure - a.s.cash_pressure,
  }[sort.value];
  return list.sort(by);
});

const engaged = computed(() => rows.value.filter((r) => r.runs > 0).length);
const atRisk = computed(() => desk.suppliers.filter((s) => s.cash_pressure >= 0.5).length);
const redQuality = computed(() => desk.suppliers.filter((s) => s.quality?.colour === 'red').length);

const open = computed<Supplier | null>(() => desk.suppliers.find((s) => s.id === route.query.s) ?? null);

function select(s: Supplier | null) {
  router.replace({ query: s ? { s: s.id } : {} });
}

const history = computed(() => (open.value ? desk.visible.filter((s) => s.suppliers.some((x) => x.id === open.value!.id)).slice(0, 8) : []));
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Suppliers</h1>
        <p class="page-sub">{{ desk.suppliers.length }} suppliers · {{ engaged }} negotiated with · {{ atRisk }} under cash pressure · {{ redQuality }} red on quality</p>
      </div>
      <div class="flex gap-2">
        <label class="search" style="width: 260px">
          <span class="material-symbols-rounded">search</span>
          <input v-model="q" placeholder="Search name, country, profile" />
        </label>
        <select v-model="sort" class="select">
          <option value="runs">Most negotiated</option>
          <option value="score">Best score</option>
          <option value="cash">Cash pressure</option>
          <option value="name">Name</option>
        </select>
      </div>
    </div>

    <div class="card rise" style="overflow: hidden">
      <table class="table">
        <thead>
          <tr>
            <th>Supplier</th>
            <th>Profile</th>
            <th>Quality</th>
            <th class="num">On time</th>
            <th>Cash pressure</th>
            <th class="num">Negotiations</th>
            <th class="num">Deals</th>
            <th class="num">Avg score</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.s.id" @click="select(r.s)">
            <td>
              <div class="flex items-center gap-3">
                <Avatar :name="r.s.name" small />
                <div class="min-w-0">
                  <div class="strong truncate" style="max-width: 300px">{{ shortName(r.s.name) }}</div>
                  <div class="text-xs text-slate-400">{{ COUNTRY_FLAG[r.s.country ?? ''] ?? '' }} {{ r.s.country }} · {{ r.s.id.replace('sup:', '#') }}</div>
                </div>
              </div>
            </td>
            <td><span class="tag">{{ humanize(r.s.archetype) }}</span></td>
            <td><span class="qdot" :class="r.s.quality?.colour"></span>{{ r.s.quality?.ppm ?? '–' }} ppm</td>
            <td class="num">{{ r.s.quality?.otd_pct ?? '–' }}%</td>
            <td>
              <div class="flex items-center gap-2">
                <div class="meter" style="width: 70px"><span :style="{ width: r.s.cash_pressure * 100 + '%', background: r.s.cash_pressure >= 0.5 ? '#d6443c' : '#2a78d6' }"></span></div>
                <span class="text-xs tabular-nums">{{ pct(r.s.cash_pressure) }}</span>
              </div>
            </td>
            <td class="num">{{ r.runs || '–' }}</td>
            <td class="num">{{ r.deals || '–' }}</td>
            <td class="num strong">{{ score100(r.avg) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <transition name="drawer">
      <div v-if="open" class="drawer-backdrop" @click.self="select(null)">
        <aside class="drawer">
          <div class="drawer-head">
            <Avatar :name="open.name" />
            <div class="min-w-0">
              <div class="text-base font-bold text-slate-900">{{ open.name }}</div>
              <div class="text-xs text-slate-400 mt-0.5">{{ COUNTRY_FLAG[open.country ?? ''] ?? '' }} {{ open.country }} · {{ humanize(open.owner_type) }} · {{ humanize(open.archetype) }}</div>
            </div>
            <button class="drawer-x" @click="select(null)"><span class="material-symbols-rounded">close</span></button>
          </div>

          <div class="stats" style="grid-template-columns: repeat(3, minmax(0, 1fr))">
            <div class="card stat">
              <div class="eyebrow">Quality</div>
              <div class="stat-value"><span class="qdot" :class="open.quality?.colour"></span>{{ open.quality?.ppm ?? '–' }}</div>
              <div class="stat-foot">ppm · {{ open.quality?.quarter }}</div>
            </div>
            <div class="card stat">
              <div class="eyebrow">On time</div>
              <div class="stat-value">{{ open.quality?.otd_pct ?? '–' }}%</div>
              <div class="stat-foot">deliveries</div>
            </div>
            <div class="card stat">
              <div class="eyebrow">Cash</div>
              <div class="stat-value">{{ pct(open.cash_pressure) }}</div>
              <div class="stat-foot">pressure</div>
            </div>
          </div>

          <div class="drawer-section">
            <span class="eyebrow">Parts and prices</span>
            <table class="table card" style="overflow: hidden">
              <thead>
                <tr><th>Part</th><th class="num">Floor</th><th class="num">Opening</th><th class="num">Best deal</th></tr>
              </thead>
              <tbody>
                <tr v-for="p in open.parts" :key="p.part_id" style="cursor: default">
                  <td class="strong">{{ p.part_id.replace('part:', '') }}</td>
                  <td class="num">{{ eur(p.floor, 2) }}</td>
                  <td class="num">{{ eur(p.opening_price, 2) }}</td>
                  <td class="num strong">{{ eur(p.best_price, 2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="history.length" class="drawer-section">
            <span class="eyebrow">Recent negotiations</span>
            <ul class="feed card" style="padding: 0.25rem 0">
              <li v-for="s in history" :key="s.key" @click="router.push(`/negotiations/${s.key}`)">
                <div class="feed-main">
                  <div class="feed-title">{{ s.title }}</div>
                  <div class="feed-sub">{{ s.case_id }} · {{ s.rounds }} rounds<template v-if="s.score !== null"> · score {{ score100(s.score) }}</template></div>
                </div>
                <span class="material-symbols-rounded text-slate-300" style="font-size: 18px">chevron_right</span>
              </li>
            </ul>
          </div>

          <div v-if="open.cash_reasons.length || open.notes.length" class="drawer-section">
            <span class="eyebrow">Notes</span>
            <div v-for="n in [...open.cash_reasons, ...open.notes]" :key="n" class="note">{{ n }}</div>
          </div>

          <div v-if="open.claims.length" class="drawer-section">
            <span class="eyebrow">Facts we can cite</span>
            <div v-for="c in open.claims" :key="c" class="note">{{ c }}</div>
          </div>
        </aside>
      </div>
    </transition>
  </div>
</template>
