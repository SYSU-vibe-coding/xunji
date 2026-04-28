import { defineStore } from 'pinia';

export type AdminPage = 'dashboard' | 'certifications' | 'content' | 'reports' | 'announcements' | 'users';

export const useAdminNavigationStore = defineStore('admin-navigation', {
  state: () => ({
    activePage: 'dashboard' as AdminPage,
  }),
  actions: {
    go(page: AdminPage) {
      this.activePage = page;
    },
  },
});
