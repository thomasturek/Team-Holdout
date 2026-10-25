import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

export interface Item {
  id: string;
  title: string;
  subtitle: string;
  tags: string;
  status: string;
  updated_at: string;
  body: string;
  facts: Record<string, string>;
}

export const TABS = [
  { key: 'open', label: 'Open' },
  { key: 'done', label: 'Done' },
] as const;

export type TabKey = (typeof TABS)[number]['key'];

const SAMPLE: Item[] = [
  {
    id: '1',
    title: 'First item',
    subtitle: 'Short description of the first item',
    tags: 'tag-a · tag-b',
    status: 'open',
    updated_at: new Date().toISOString(),
    body: 'Main content for the first item goes here.',
    facts: { Owner: 'Someone', State: 'Open' },
  },
  {
    id: '2',
    title: 'Second item',
    subtitle: 'Short description of the second item',
    tags: 'tag-c',
    status: 'open',
    updated_at: new Date(Date.now() - 86400000).toISOString(),
    body: 'Main content for the second item goes here.',
    facts: { Owner: 'Someone else', State: 'Open' },
  },
  {
    id: '3',
    title: 'Third item',
    subtitle: 'Already finished',
    tags: 'tag-a',
    status: 'done',
    updated_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    body: 'Main content for the third item goes here.',
    facts: { Owner: 'Someone', State: 'Done' },
  },
];

export const useWorkspace = defineStore('workspace', () => {
  const all = ref<Item[]>([]);
  const status = ref<TabKey>('open');
  const activeId = ref<string | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const drawerOpen = ref(false);

  const items = computed(() => all.value.filter((it) => it.status === status.value));
  const selected = computed(() => all.value.find((it) => it.id === activeId.value) ?? null);
  const openCount = computed(() => all.value.filter((it) => it.status === 'open').length);

  async function load() {
    loading.value = true;
    error.value = null;
    try {
      all.value = SAMPLE;
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    } finally {
      loading.value = false;
    }
  }

  function switchTab(key: TabKey) {
    status.value = key;
    activeId.value = null;
  }

  function open(it: Item) {
    activeId.value = it.id;
  }

  function closePanels() {
    drawerOpen.value = false;
  }

  return { all, status, activeId, loading, error, drawerOpen, items, selected, openCount, load, switchTab, open, closePanels };
});
