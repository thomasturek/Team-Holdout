<script setup lang="ts">
import type { SessionStatus } from '@/api/types';
import { STATUS } from '@/format';

defineProps<{ status: SessionStatus }>();
</script>

<template>
  <span class="pill" :class="STATUS[status].tone">
    <span v-if="status === 'live'" class="dot"></span>
    <span v-else class="material-symbols-rounded">{{ STATUS[status].icon }}</span>
    {{ STATUS[status].label }}
  </span>
</template>
