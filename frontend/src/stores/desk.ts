import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { fetchSession, fetchSessions, fetchSuppliers } from '@/api/data';
import type { SessionDetail, SessionSummary, Supplier } from '@/api/types';
import { POLL_MS } from '@/app';
import { shortName } from '@/format';

export interface Toast {
  id: number;
  title: string;
  text: string;
  tone: string;
  key: string;
}

export const useDesk = defineStore('desk', () => {
  const sessions = ref<SessionSummary[]>([]);
  const suppliers = ref<Supplier[]>([]);
  const setFilter = ref<string>('all');
  const fresh = ref<Set<string>>(new Set());
  const toasts = ref<Toast[]>([]);
  const error = ref<string | null>(null);
  const loaded = ref(false);
  const detail = ref<SessionDetail | null>(null);
  const detailKey = ref<string | null>(null);
  let timer: ReturnType<typeof setInterval> | null = null;
  let toastId = 0;
  const known = new Map<string, string>();

  const sets = computed(() => [...new Set(sessions.value.map((s) => s.set))].sort());
  const visible = computed(() => (setFilter.value === 'all' ? sessions.value : sessions.value.filter((s) => s.set === setFilter.value)));
  const liveCount = computed(() => visible.value.filter((s) => s.status === 'live').length);
  const supplierById = computed(() => new Map(suppliers.value.map((s) => [s.id, s])));

  function pushToast(t: Omit<Toast, 'id'>) {
    const id = ++toastId;
    toasts.value = [...toasts.value.slice(-3), { ...t, id }];
    setTimeout(() => (toasts.value = toasts.value.filter((x) => x.id !== id)), 6000);
  }

  function markFresh(key: string) {
    fresh.value = new Set([...fresh.value, key]);
    setTimeout(() => {
      const next = new Set(fresh.value);
      next.delete(key);
      fresh.value = next;
    }, 12000);
  }

  function diff(next: SessionSummary[]) {
    if (!loaded.value) {
      for (const s of next) known.set(s.key, s.status);
      return;
    }
    for (const s of next) {
      const before = known.get(s.key);
      const who = s.suppliers.map((x) => shortName(x.name)).join(', ');
      if (before === undefined) {
        markFresh(s.key);
        pushToast({ title: 'New negotiation', text: `${who} · ${s.title}`, tone: 'live', key: s.key });
      } else if (before !== s.status && s.status === 'deal') {
        markFresh(s.key);
        pushToast({ title: 'Deal closed', text: `${shortName(s.deal_supplier ?? who)} · score ${Math.round((s.score ?? 0) * 100)}`, tone: 'good', key: s.key });
      } else if (before !== s.status && (s.status === 'no_deal' || s.status === 'walked' || s.status === 'timeout')) {
        pushToast({ title: 'Negotiation ended', text: `${who} · no deal`, tone: 'critical', key: s.key });
      }
      known.set(s.key, s.status);
    }
  }

  async function refresh() {
    try {
      const next = await fetchSessions();
      diff(next);
      sessions.value = next;
      loaded.value = true;
      error.value = null;
      if (detailKey.value) {
        const s = next.find((x) => x.key === detailKey.value);
        if (s && detail.value && s.updated_at !== detail.value.updated_at) detail.value = await fetchSession(s.key);
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  }

  async function loadSuppliers() {
    if (suppliers.value.length) return;
    try {
      suppliers.value = await fetchSuppliers();
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  }

  async function select(key: string | null) {
    detailKey.value = key;
    if (!key) {
      detail.value = null;
      return;
    }
    if (detail.value?.key === key) return;
    try {
      const d = await fetchSession(key);
      if (detailKey.value === key) detail.value = d;
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  }

  function start() {
    if (timer) return;
    refresh();
    loadSuppliers();
    timer = setInterval(refresh, POLL_MS);
  }

  return { sessions, suppliers, setFilter, sets, visible, liveCount, fresh, toasts, error, loaded, detail, detailKey, supplierById, refresh, select, start, loadSuppliers };
});
