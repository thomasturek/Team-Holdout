<script setup lang="ts">
import { useWorkspace } from '@/stores/workspace';

const ws = useWorkspace();
</script>

<template>
  <Teleport to="#header-stats">
    <div class="flex items-center gap-1.5 text-xs text-slate-500">
      <span class="rounded border border-slate-200/80 bg-white/70 px-2.5 py-1">
        <b class="font-semibold tabular-nums text-slate-900">{{ ws.all.length }}</b> total
      </span>
      <span class="rounded border border-slate-200/80 bg-white/70 px-2.5 py-1">
        <b class="font-semibold tabular-nums text-slate-900">{{ ws.openCount }}</b> open
      </span>
    </div>
  </Teleport>
</template>
