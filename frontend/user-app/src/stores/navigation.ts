import { defineStore } from 'pinia';

export type UserPage = 'home' | 'search' | 'publish' | 'matches' | 'messages' | 'profile' | 'lost-detail';

export const useNavigationStore = defineStore('user-navigation', {
  state: () => ({
    activePage: 'home' as UserPage,
  }),
  actions: {
    go(page: UserPage) {
      this.activePage = page;
    },
  },
});
