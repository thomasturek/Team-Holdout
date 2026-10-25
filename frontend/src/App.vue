<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router';
import { navItems } from '@/router';
import { useLoadingStore } from '@/stores/loading';
import { APP_ICON, APP_NAME } from '@/app';

const loading = useLoadingStore();
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
      class="sticky top-0 z-30 border-b border-slate-300/30 bg-white/50 backdrop-blur-2xl backdrop-saturate-150"
    >
      <div class="grid h-14 grid-cols-[1fr_auto_1fr] items-center gap-4 pl-2 pr-6">
        <div class="flex min-w-0 items-center gap-2.5 justify-self-start">
          <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-slate-900 text-white shadow-sm">
            <span class="material-symbols-rounded text-[26px] leading-none">{{ APP_ICON }}</span>
          </div>
          <div class="truncate text-lg font-bold tracking-tight text-slate-900">{{ APP_NAME }}</div>
        </div>

        <nav class="hidden items-center justify-center md:flex">
          <div class="flex items-center gap-0.5 rounded border border-slate-200/80 bg-slate-50/80 p-1">
            <RouterLink
              v-for="item in navItems"
              :key="item.to"
              :to="item.to"
              class="flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-semibold text-slate-500 transition hover:text-slate-900"
              active-class="!bg-slate-900 !text-white shadow-sm"
            >
              <span class="material-symbols-rounded text-[15px] leading-none opacity-80">{{ item.icon }}</span>
              {{ item.label }}
            </RouterLink>
          </div>
        </nav>

        <div id="header-stats" class="flex items-center justify-self-end"></div>
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
</template>

<style>
.splash { position: fixed; inset: 0; z-index: 100; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.9rem; background: rgba(255,255,255,0.55); backdrop-filter: blur(40px) saturate(180%); -webkit-backdrop-filter: blur(40px) saturate(180%); }
.splash-logo { border-radius: 6px; display: flex; align-items: center; justify-content: center; width: 72px; height: 72px; background: #0f172a; color: #fff; box-shadow: 0 10px 30px rgba(15,23,42,0.18); }
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
