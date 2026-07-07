import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

import { useAuthStore } from '@/stores/auth';

const routes: RouteRecordRaw[] = [
  {
    path: '/auth',
    component: () => import('@/layouts/AuthLayout.vue'),
    meta: { public: true },
    children: [
      { path: '', redirect: { name: 'admin-login' } },
      { path: 'login', name: 'admin-login', component: () => import('@/views/auth/LoginView.vue') },
    ],
  },
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    children: [
      { path: '', redirect: { name: 'dashboard' } },
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
      {
        path: 'certifications',
        name: 'certifications',
        component: () => import('@/views/CertificationListView.vue'),
      },
      { path: 'reviews', name: 'reviews', component: () => import('@/views/ContentReviewView.vue') },
      { path: 'reports', name: 'reports', component: () => import('@/views/ReportListView.vue') },
      {
        path: 'announcements',
        name: 'announcements',
        component: () => import('@/views/AnnouncementView.vue'),
      },
      { path: 'matches', name: 'matches', component: () => import('@/views/MatchView.vue') },
      {
        path: 'operation-logs',
        name: 'operation-logs',
        component: () => import('@/views/OperationLogView.vue'),
      },
      { path: 'users', name: 'admin-users', component: () => import('@/views/UserListView.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  const isPublic = to.matched.some((r) => r.meta?.public);
  if (!isPublic) {
    if (!auth.token) return { name: 'admin-login', query: { redirect: to.fullPath } };
    if (auth.profile && auth.profile.role !== 'ADMIN') {
      auth.clear();
      return { name: 'admin-login' };
    }
  }
  if (isPublic && auth.token && auth.profile?.role === 'ADMIN' && to.name === 'admin-login') {
    return { name: 'dashboard' };
  }
  return true;
});

export default router;
