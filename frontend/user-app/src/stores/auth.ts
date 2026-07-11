import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import type { LoginResponse, UserProfile } from '@xunji/shared';

import {
  clearStoredToken,
  getStoredToken,
  isAuthApiError,
  registerUnauthorizedHandler,
  setStoredToken,
} from '@/api/http';
import { getMyProfile } from '@/api/user';
import router from '@/router';

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getStoredToken());
  const profile = ref<UserProfile | null>(null);
  const initializing = ref(false);
  let profilePromise: Promise<UserProfile> | null = null;
  let profilePromiseToken: string | null = null;

  const isAuthenticated = computed(() => Boolean(token.value));
  const displayName = computed(() => profile.value?.nickname ?? '同学');
  const initial = computed(() => (profile.value?.nickname?.slice(0, 1) ?? '同'));

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
    if (!token.value || initializing.value) return;
    initializing.value = true;
    try {
      await loadProfile();
    } catch (err) {
      if (isAuthApiError(err)) {
        clear();
        return;
      }
      throw err;
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
