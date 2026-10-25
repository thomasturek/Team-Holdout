<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router';
import { navItems } from '@/router';
import { useLoadingStore } from '@/stores/loading';
import { onMounted } from 'vue';
import { APP_ICON, APP_NAME } from '@/app';
import { useDesk } from '@/stores/desk';
import Toasts from '@/components/Toasts.vue';

const loading = useLoadingStore();
const desk = useDesk();

onMounted(() => desk.start());
</script>

<template>
  <transition name="splash">
    <div v-if="!loading.booted" class="splash">
      <div class="splash-logo">
        <span class="material-symbols-rounded">{{ APP_ICON }}</span>
      </div>
      <div class="splash-name">{{ APP_NAME }}</div>
      <div class="loading-track splash-track"><div class="loading-run"></div></div>
    </div>
  </transition>
  <div v-if="loading.booted && loading.busy" class="loading-track top-bar"><div class="loading-run"></div></div>
  <div class="h-screen flex flex-col">
    <header
      class="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur-xl backdrop-saturate-150"
    >
      <div class="grid h-14 grid-cols-[1fr_auto_1fr] items-center gap-4 pl-4 pr-5">
        <div class="flex min-w-0 items-center gap-2.5 justify-self-start">
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white shadow-sm">
            <span class="material-symbols-rounded text-[22px] leading-none">{{ APP_ICON }}</span>
          </div>
          <div class="truncate text-lg font-bold tracking-tight text-slate-900">{{ APP_NAME }}</div>
        </div>

        <nav class="hidden items-center justify-center md:flex">
          <div class="flex items-center gap-0.5 rounded-lg bg-slate-100 p-1">
            <RouterLink
              v-for="item in navItems"
              :key="item.to"
              :to="item.to"
              class="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold text-slate-500 transition hover:text-slate-900"
              active-class="!bg-white !text-slate-900 shadow-sm"
            >
              <span class="material-symbols-rounded text-[15px] leading-none opacity-80">{{ item.icon }}</span>
              {{ item.label }}
            </RouterLink>
          </div>
        </nav>

        <div class="flex items-center gap-3 justify-self-end">
          <span v-if="desk.liveCount" class="pill live"><span class="dot"></span>{{ desk.liveCount }} live</span>
          <div v-if="desk.sets.length > 1" class="seg">
            <button :class="{ active: desk.setFilter === 'all' }" @click="desk.setFilter = 'all'">All</button>
            <button v-for="s in desk.sets" :key="s" :class="{ active: desk.setFilter === s }" @click="desk.setFilter = s">{{ s[0].toUpperCase() + s.slice(1) }}</button>
          </div>
        </div>
      </div>

      <nav class="flex flex-col gap-1 border-t border-slate-100 px-3 py-1.5 md:hidden">
        <div class="flex gap-1 overflow-x-auto">
          <RouterLink
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="whitespace-nowrap rounded px-3 py-1 text-xs font-semibold text-slate-500"
            active-class="bg-slate-900 text-white"
          >
            {{ item.label }}
          </RouterLink>
        </div>
      </nav>
    </header>

    <main class="relative flex-1 min-h-0 overflow-y-auto">
      <RouterView v-slot="{ Component }">
        <component :is="Component" />
      </RouterView>
    </main>
  </div>
  <Toasts />
</template>

<style>
.splash { position: fixed; inset: 0; z-index: 100; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.9rem; background: rgba(255,255,255,0.55); backdrop-filter: blur(40px) saturate(180%); -webkit-backdrop-filter: blur(40px) saturate(180%); }
.splash-logo { border-radius: 16px; display: flex; align-items: center; justify-content: center; width: 72px; height: 72px; background: #0f172a; color: #fff; box-shadow: 0 10px 30px rgba(15,23,42,0.18); }
.splash-logo .material-symbols-rounded { font-size: 44px; }
.splash-name { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; color: #0f172a; }
.loading-track { position: relative; overflow: hidden; background: rgba(15,23,42,0.08); }
.loading-run { position: absolute; top: 0; bottom: 0; width: 35%; background: #0f172a; animation: loading-run 1.1s ease-in-out infinite; }
.splash-track { border-radius: 2px; width: 180px; height: 3px; margin-top: 0.6rem; }
.top-bar { position: fixed; top: 0; left: 0; right: 0; z-index: 90; height: 2px; background: transparent; }
@keyframes loading-run { from { left: -35%; } to { left: 100%; } }
.splash-leave-active { transition: opacity 0.35s ease; }
.splash-leave-to { opacity: 0; }
</style>
