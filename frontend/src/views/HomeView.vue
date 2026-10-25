<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import { useWorkspace } from '@/stores/workspace';
import HeaderStats from '@/components/HeaderStats.vue';
import ListPane from '@/components/ListPane.vue';
import DetailPane from '@/components/DetailPane.vue';
import SideDrawer from '@/components/SideDrawer.vue';

const ws = useWorkspace();

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') ws.closePanels();
}

onMounted(() => {
  ws.load();
  window.addEventListener('keydown', onKeydown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown);
});
</script>

<template>
  <div class="workspace">
    <HeaderStats />
    <p v-if="ws.error" class="error">{{ ws.error }}</p>
    <div class="body">
      <ListPane />
      <DetailPane />
    </div>
    <SideDrawer />
  </div>
</template>
