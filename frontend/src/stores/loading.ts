import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

const MIN_SPLASH_MS = 500;
const MAX_SPLASH_MS = 10000;

export const useLoadingStore = defineStore('loading', () => {
  const pending = ref(0);
  const booted = ref(false);
  const startedAt = Date.now();
  let seenRequest = false;

  const busy = computed(() => pending.value > 0);

  function finishBoot() {
    if (booted.value) return;
    const wait = MIN_SPLASH_MS - (Date.now() - startedAt);
    if (wait > 0) setTimeout(finishBoot, wait);
    else booted.value = true;
  }

  function start() {
    seenRequest = true;
    pending.value += 1;
  }

  function stop() {
    pending.value = Math.max(0, pending.value - 1);
    if (pending.value === 0 && seenRequest) finishBoot();
  }

  setTimeout(() => {
    if (!seenRequest) finishBoot();
  }, MIN_SPLASH_MS);
  setTimeout(() => (booted.value = true), MAX_SPLASH_MS);

  return { pending, booted, busy, start, stop };
});
