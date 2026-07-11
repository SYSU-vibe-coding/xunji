import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

import { useAuthStore } from '@/stores/auth';

const routes: RouteRecordRaw[] = [
  {
    path: '/auth',
    component: () => import('@/layouts/AuthLayout.vue'),
    meta: { public: true },
    children: [
      { path: '', redirect: { name: 'login' } },
      { path: 'login', name: 'login', component: () => import('@/views/auth/LoginView.vue') },
      { path: 'register', name: 'register', component: () => import('@/views/auth/RegisterView.vue') },
    ],
  },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    children: [
      // meta.tab=true 表示底部 dock 主 tab，顶栏不显示返回按钮
      { path: '', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { tab: true } },
      { path: 'search', name: 'search', component: () => import('@/views/SearchView.vue'), meta: { tab: true } },
      { path: 'publish/lost', name: 'publish-lost', component: () => import('@/views/PublishLostView.vue') },
      { path: 'publish/found', name: 'publish-found', component: () => import('@/views/PublishFoundView.vue') },
      {
        path: 'items/:bizType(lost|found)/:id',
        name: 'item-detail',
        component: () => import('@/views/ItemDetailView.vue'),
      },
      { path: 'matches', name: 'matches', component: () => import('@/views/MatchListView.vue') },
      { path: 'claims', name: 'my-claims', component: () => import('@/views/claim/MyClaimsView.vue') },
      {
        path: 'claims/:id',
        name: 'claim-detail',
        component: () => import('@/views/claim/ClaimDetailView.vue'),
      },
      { path: 'notifications', name: 'notifications', component: () => import('@/views/NotificationsView.vue'), meta: { tab: true } },
      {
        path: 'announcements',
        name: 'announcements',
        component: () => import('@/views/AnnouncementListView.vue'),
      },
      {
        path: 'announcements/:id',
        name: 'announcement-detail',
        component: () => import('@/views/AnnouncementDetailView.vue'),
      },
      { path: 'profile', name: 'profile', component: () => import('@/views/profile/ProfileView.vue'), meta: { tab: true } },
      { path: 'profile/items', name: 'my-items', component: () => import('@/views/profile/MyItemsView.vue') },
      {
        path: 'profile/certification',
        name: 'certification',
        component: () => import('@/views/profile/CertificationView.vue'),
      },
      { path: 'profile/credits', name: 'credits', component: () => import('@/views/profile/CreditsView.vue') },
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
  if (!isPublic && !auth.token) {
    return { name: 'login', query: { redirect: to.fullPath } };
  }
  if (isPublic && auth.token && (to.name === 'login' || to.name === 'register')) {
    return { name: 'home' };
  }
  return true;
});

export default router;
