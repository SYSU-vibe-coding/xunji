import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import type { LoginResponse, UserProfile } from '@xunji/shared';

import {
  clearStoredToken,
  getStoredToken,
  registerUnauthorizedHandler,
  setStoredToken,
} from '@/api/http';
import { getMyProfile } from '@/api/auth';
import router from '@/router';

export const useAuthStore = defineStore('admin-auth', () => {
  const token = ref<string | null>(getStoredToken());
  const profile = ref<UserProfile | null>(null);
  const initializing = ref(false);

  const isAuthenticated = computed(() => Boolean(token.value));
  const isAdmin = computed(() => profile.value?.role === 'ADMIN');
  const displayName = computed(() => profile.value?.nickname ?? '管理员');

  function setSession(payload: LoginResponse): void {
    token.value = payload.token;
    setStoredToken(payload.token);
  }

  async function loadProfile(): Promise<UserProfile | null> {
    if (!token.value) return null;
    const fresh = await getMyProfile();
    profile.value = fresh;
    return fresh;
  }

  async function restore(): Promise<void> {
    if (!token.value || initializing.value) return;
    initializing.value = true;
    try {
      const me = await loadProfile();
      if (me?.role !== 'ADMIN') clear();
    } catch {
      clear();
    } finally {
      initializing.value = false;
    }
  }

  function clear(): void {
    token.value = null;
    profile.value = null;
    clearStoredToken();
  }

  function logout(): void {
    clear();
    if (router.currentRoute.value.name !== 'admin-login') {
      void router.push({ name: 'admin-login' });
    }
  }

  registerUnauthorizedHandler(() => {
    clear();
    if (router.currentRoute.value.name !== 'admin-login') {
      void router.push({ name: 'admin-login' });
    }
  });

  return {
    token,
    profile,
    isAuthenticated,
    isAdmin,
    displayName,
    setSession,
    loadProfile,
    restore,
    clear,
    logout,
  };
});
