<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useDesk } from '@/stores/desk';

const desk = useDesk();
const router = useRouter();

const ICONS: Record<string, string> = { live: 'bolt', good: 'handshake', critical: 'block' };

function go(key: string) {
  router.push(`/negotiations/${key}`);
}
</script>

<template>
  <div class="toasts">
    <transition-group name="toast">
      <div v-for="t in desk.toasts" :key="t.id" class="toast" :class="t.tone" @click="go(t.key)">
        <span class="material-symbols-rounded">{{ ICONS[t.tone] ?? 'notifications' }}</span>
        <div>
          <div class="toast-title">{{ t.title }}</div>
          <div class="toast-text">{{ t.text }}</div>
        </div>
      </div>
    </transition-group>
  </div>
</template>
