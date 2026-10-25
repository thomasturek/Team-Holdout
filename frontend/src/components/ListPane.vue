<script setup lang="ts">
import { useWorkspace, TABS } from '@/stores/workspace';
import { fmtListDate } from '@/format';

const ws = useWorkspace();
</script>

<template>
  <aside class="list-pane">
    <div class="list-head">
      <div class="seg">
        <button v-for="t in TABS" :key="t.key" :class="{ active: ws.status === t.key }" @click="ws.switchTab(t.key)">
          {{ t.label }}<span v-if="t.key === 'open'" class="count">{{ ws.openCount }}</span>
        </button>
      </div>
      <button class="icon-btn" title="New" @click="ws.drawerOpen = true">
        <span class="material-symbols-rounded">add</span>
      </button>
      <button class="icon-btn" title="Reload" :disabled="ws.loading" @click="ws.load()">
        <span class="material-symbols-rounded" :class="{ spin: ws.loading }">refresh</span>
      </button>
    </div>
    <ul class="list">
      <li v-for="it in ws.items" :key="it.id" :class="['row', { sel: ws.activeId === it.id }]" @click="ws.open(it)">
        <div class="row-top">
          <span class="row-title">{{ it.title }}</span>
          <span class="when">{{ fmtListDate(it.updated_at) }}</span>
        </div>
        <div class="subj">{{ it.subtitle }}</div>
        <div class="row-meta">
          <span class="row-tags">{{ it.tags }}</span>
          <span class="act">Open ›</span>
        </div>
      </li>
      <li v-if="!ws.loading && ws.items.length === 0" class="muted-row">Nothing here yet.</li>
    </ul>
  </aside>
</template>
