import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { APP_NAME } from '@/app';

const HomeView = () => import('@/views/HomeView.vue');

export interface NavItem {
  to: string;
  label: string;
  icon: string;
}

export const navItems: NavItem[] = [
  { to: '/', label: 'Home', icon: 'dashboard' },
];

const routes: RouteRecordRaw[] = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/:pathMatch(.*)*', redirect: '/' },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.afterEach(() => {
  document.title = APP_NAME;
});
