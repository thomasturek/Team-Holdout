<script setup lang="ts">
import { useWorkspace } from '@/stores/workspace';

const ws = useWorkspace();
</script>

<template>
  <transition name="drawer">
    <div v-if="ws.drawerOpen" class="drawer-backdrop">
      <aside class="drawer">
        <header class="drawer-head">
          <h3>New item</h3>
          <button class="drawer-x" title="Close" @click="ws.drawerOpen = false"><span class="material-symbols-rounded">close</span></button>
        </header>
        <label class="fld">Title<input type="text" /></label>
        <label class="fld">Notes<textarea rows="8"></textarea></label>
        <div class="drawer-actions">
          <button class="btn primary">Save</button>
          <button class="btn ghost" @click="ws.drawerOpen = false">Cancel</button>
        </div>
      </aside>
    </div>
  </transition>
</template>
