import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import type { LoginResponse, UserProfile } from '@xunji/shared';

import { clearStoredToken, getStoredToken, registerUnauthorizedHandler, setStoredToken } from '@/api/http';
import { getMyProfile } from '@/api/user';
import router from '@/router';

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getStoredToken());
  const profile = ref<UserProfile | null>(null);
  const initializing = ref(false);

  const isAuthenticated = computed(() => Boolean(token.value));
  const displayName = computed(() => profile.value?.nickname ?? '同学');
  const initial = computed(() => (profile.value?.nickname?.slice(0, 1) ?? '同'));

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
      await loadProfile();
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
    if (router.currentRoute.value.name !== 'login') {
      void router.push({ name: 'login' });
    }
  }

  registerUnauthorizedHandler(() => {
    clear();
    if (router.currentRoute.value.name !== 'login') {
      void router.push({ name: 'login' });
    }
  });

  return {
    token,
    profile,
    isAuthenticated,
    displayName,
    initial,
    setSession,
    loadProfile,
    restore,
    clear,
    logout,
  };
});
