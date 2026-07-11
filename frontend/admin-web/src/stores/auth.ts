import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import type { LoginResponse, UserProfile } from '@xunji/shared';

import {
  clearStoredToken,
  getStoredToken,
  isUnauthorizedApiError,
  registerUnauthorizedHandler,
  setStoredToken,
} from '@/api/http';
import { getMyProfile } from '@/api/auth';
import router from '@/router';

export const useAuthStore = defineStore('admin-auth', () => {
  const token = ref<string | null>(getStoredToken());
  const profile = ref<UserProfile | null>(null);
  const initializing = ref(false);
  const initialized = ref(false);
  let restorePromise: Promise<void> | null = null;
  let profilePromise: Promise<UserProfile> | null = null;
  let profilePromiseToken: string | null = null;

  const isAuthenticated = computed(() => Boolean(token.value));
  const isAdmin = computed(() => profile.value?.role === 'ADMIN');
  const displayName = computed(() => profile.value?.nickname ?? '管理员');

  function setSession(payload: LoginResponse): void {
    token.value = payload.token;
    profile.value = null;
    setStoredToken(payload.token);
  }

  async function loadProfile(): Promise<UserProfile | null> {
    if (!token.value) return null;
    const requestToken = token.value;
    if (profilePromise && profilePromiseToken === requestToken) return profilePromise;
    profilePromiseToken = requestToken;
    const currentPromise = getMyProfile()
      .then((fresh) => {
        if (token.value === requestToken) profile.value = fresh;
        return fresh;
      })
      .finally(() => {
        if (profilePromiseToken === requestToken) {
          profilePromise = null;
          profilePromiseToken = null;
        }
      });
    profilePromise = currentPromise;
    return currentPromise;
  }

  async function restore(): Promise<void> {
    if (initialized.value) return;
    if (restorePromise) return restorePromise;
    restorePromise = (async () => {
      initializing.value = true;
      try {
        if (!token.value) return;
        const me = await loadProfile();
        if (me?.role !== 'ADMIN') logout();
      } catch (err) {
        if (isUnauthorizedApiError(err)) logout();
      } finally {
        initializing.value = false;
        initialized.value = true;
      }
    })();
    return restorePromise;
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
    initialized,
    initializing,
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
