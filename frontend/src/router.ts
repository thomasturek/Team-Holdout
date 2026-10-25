import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { APP_NAME } from '@/app';

const OverviewView = () => import('@/views/OverviewView.vue');
const NegotiationsView = () => import('@/views/NegotiationsView.vue');
const SuppliersView = () => import('@/views/SuppliersView.vue');

export interface NavItem {
  to: string;
  label: string;
  icon: string;
}

export const navItems: NavItem[] = [
  { to: '/overview', label: 'Overview', icon: 'space_dashboard' },
  { to: '/negotiations', label: 'Negotiations', icon: 'forum' },
  { to: '/suppliers', label: 'Suppliers', icon: 'factory' },
];

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/overview' },
  { path: '/overview', name: 'overview', component: OverviewView, meta: { title: 'Overview' } },
  { path: '/negotiations/:set?/:id?', name: 'negotiations', component: NegotiationsView, meta: { title: 'Negotiations' } },
  { path: '/suppliers', name: 'suppliers', component: SuppliersView, meta: { title: 'Suppliers' } },
  { path: '/:pathMatch(.*)*', redirect: '/overview' },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · ${APP_NAME}` : APP_NAME;
});
