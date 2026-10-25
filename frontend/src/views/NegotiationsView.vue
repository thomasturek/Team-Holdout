<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDesk } from '@/stores/desk';
import type { SessionSummary } from '@/api/types';
import StatusPill from '@/components/StatusPill.vue';
import Avatar from '@/components/Avatar.vue';
import NegotiationDetail from '@/components/NegotiationDetail.vue';
import { ago, score100, shortName } from '@/format';

const desk = useDesk();
const route = useRoute();
const router = useRouter();

const TABS = [
  { key: 'all', label: 'All' },
  { key: 'live', label: 'Live' },
  { key: 'deal', label: 'Deals' },
  { key: 'other', label: 'No deal' },
] as const;

const tab = ref<(typeof TABS)[number]['key']>('all');
const q = ref('');
const caseFilter = ref<string>((route.query.case as string) || '');

const key = computed(() => (route.params.set && route.params.id ? `${route.params.set}/${route.params.id}` : null));

const caseOptions = computed(() => {
  const m = new Map<string, string>();
  for (const s of desk.visible) m.set(s.case_id, s.title);
  return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]));
});

function inTab(s: SessionSummary, t: string) {
  if (t === 'live') return s.status === 'live';
  if (t === 'deal') return s.status === 'deal';
  if (t === 'other') return s.status !== 'deal' && s.status !== 'live';
  return true;
}

const filtered = computed(() => {
  const needle = q.value.trim().toLowerCase();
  return desk.visible.filter((s) => {
    if (!inTab(s, tab.value)) return false;
    if (caseFilter.value && s.case_id !== caseFilter.value) return false;
    if (!needle) return true;
    return [s.title, s.case_id, s.session_id, ...s.suppliers.map((x) => x.name)].join(' ').toLowerCase().includes(needle);
  });
});

const counts = computed(() => Object.fromEntries(TABS.map((t) => [t.key, desk.visible.filter((s) => inTab(s, t.key) && (!caseFilter.value || s.case_id === caseFilter.value)).length])));

watch(
  key,
  (k) => {
    if (k) desk.select(k);
    else desk.select(null);
  },
  { immediate: true },
);

watch(
  () => [desk.loaded, filtered.value.length] as const,
  ([loaded]) => {
    if (loaded && !key.value && filtered.value.length && window.innerWidth > 1100) open(filtered.value[0]);
  },
  { immediate: true },
);

watch(caseFilter, (c) => router.replace({ query: c ? { case: c } : {} }));

function open(s: SessionSummary) {
  router.push({ path: `/negotiations/${s.key}`, query: route.query });
}

function names(s: SessionSummary) {
  return s.suppliers.map((x) => shortName(x.name)).join(', ');
}
</script>

<template>
  <div class="split" :class="{ 'has-detail': !!key }">
    <aside class="list-pane">
      <div class="list-tools">
        <div class="seg">
          <button v-for="t in TABS" :key="t.key" :class="{ active: tab === t.key }" @click="tab = t.key">
            {{ t.label }}<span class="count">{{ counts[t.key] }}</span>
          </button>
        </div>
        <div class="row-tools">
          <label class="search flex-1">
            <span class="material-symbols-rounded">search</span>
            <input v-model="q" placeholder="Search supplier, case, session" />
          </label>
          <select v-model="caseFilter" class="select" style="max-width: 120px">
            <option value="">All cases</option>
            <option v-for="[id, title] in caseOptions" :key="id" :value="id" :title="title">{{ id.replace('case:', '') }}</option>
          </select>
        </div>
      </div>
      <ul class="list">
        <li v-for="s in filtered" :key="s.key" class="item" :class="{ sel: key === s.key, fresh: desk.fresh.has(s.key) }" @click="open(s)">
          <Avatar :name="s.deal_supplier ?? s.suppliers[0]?.name ?? s.title" />
          <div class="item-main">
            <div class="item-top">
              <span class="item-name">{{ names(s) }}</span>
              <span class="item-when">{{ ago(s.updated_at) }}</span>
            </div>
            <div class="item-sub">{{ s.title }}</div>
            <div class="item-meta">
              <StatusPill :status="s.status" />
              <span class="tag">{{ s.case_id.replace('case:', '') }}</span>
              <span class="tag">{{ s.rounds }} rd</span>
              <span v-if="s.score !== null" class="item-score">{{ score100(s.score) }}</span>
            </div>
          </div>
        </li>
        <li v-if="desk.loaded && !filtered.length" class="empty">
          <span class="material-symbols-rounded">inbox</span>
          Nothing matches these filters.
        </li>
      </ul>
    </aside>

    <section class="detail">
      <NegotiationDetail v-if="desk.detail && desk.detail.key === key" :d="desk.detail" @back="router.push('/negotiations')" />
      <div v-else class="empty" style="padding-top: 20vh">
        <span class="material-symbols-rounded">forum</span>
        {{ key ? 'Loading…' : 'Pick a negotiation on the left.' }}
      </div>
    </section>
  </div>
</template>
