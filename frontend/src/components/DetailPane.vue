<script setup lang="ts">
import { useWorkspace } from '@/stores/workspace';
import { fmtDate } from '@/format';
import { APP_ICON, APP_NAME } from '@/app';

const ws = useWorkspace();
</script>

<template>
  <section v-if="ws.selected" class="detail">
    <header class="detail-head">
      <h2>{{ ws.selected.title }}</h2>
      <div class="meta">
        <span>{{ ws.selected.subtitle }}</span>
        <span>{{ fmtDate(ws.selected.updated_at) }}</span>
      </div>
    </header>

    <div class="hero">
      <span class="eyebrow">Summary</span>
      <p class="hero-title">Headline for this item</p>
      <p class="hero-text">One or two lines that explain the most important thing about it.</p>
    </div>

    <div class="actions">
      <button class="btn primary">Primary action</button>
      <button class="btn ghost" @click="ws.drawerOpen = true">Secondary</button>
    </div>

    <div class="detail-grid">
      <div class="detail-main">
        <div class="panel">
          <pre class="panel-text">{{ ws.selected.body }}</pre>
        </div>
      </div>
      <aside class="detail-side dossier">
        <div class="side-block">
          <div class="side-label"><span class="material-symbols-rounded side-icon">info</span>Details</div>
          <dl class="facts">
            <template v-for="(v, k) in ws.selected.facts" :key="k">
              <dt>{{ k }}</dt>
              <dd>{{ v }}</dd>
            </template>
          </dl>
        </div>
      </aside>
    </div>
  </section>
  <section v-else class="detail placeholder">
    <div class="ph">
      <span class="ph-icon material-symbols-rounded">{{ APP_ICON }}</span>
      <p class="ph-name">{{ APP_NAME }}</p>
    </div>
  </section>
</template>
