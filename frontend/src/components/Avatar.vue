<script setup lang="ts">
import { computed } from 'vue';
import { initials } from '@/format';

const props = defineProps<{ name: string; small?: boolean; us?: boolean }>();

const COLORS = ['#4f46e5', '#0f766e', '#b45309', '#be185d', '#1d4ed8', '#7c3aed', '#15803d', '#c2410c', '#0e7490', '#9f1239'];

const bg = computed(() => {
  let h = 0;
  for (const ch of props.name) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return COLORS[h % COLORS.length];
});
</script>

<template>
  <span class="avatar" :class="{ sm: small, us }" :style="us ? undefined : { background: bg }">{{ us ? 'US' : initials(name) }}</span>
</template>
