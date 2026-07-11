<script setup lang="ts">
import { onMounted, watch } from 'vue';
import { RouterView, useRoute } from 'vue-router';

import AppHeader from '@/components/AppHeader.vue';
import AppMobileDock from '@/components/AppMobileDock.vue';
import AppSidebar from '@/components/AppSidebar.vue';
import { useAuthStore } from '@/stores/auth';
import { useNotificationStore } from '@/stores/notification';

const auth = useAuthStore();
const notice = useNotificationStore();
const route = useRoute();

onMounted(async () => {
  if (auth.token && !auth.profile) {
    await auth.loadProfile().catch(() => {});
  }
  if (auth.token) await notice.refresh();
});

// 仅在页面类型变化时刷新，query 更新不应重复请求未读数。
watch(
  () => route.name,
  () => {
    if (auth.token) void notice.refresh();
  },
);
</script>

<template>
  <div class="app-shell">
    <AppSidebar class="sidebar-desktop" />
    <div class="main">
      <AppHeader />
      <main class="content">
        <RouterView v-slot="{ Component, route: r }">
          <Transition name="fade-slide" mode="out-in">
            <component :is="Component" :key="r.path" />
          </Transition>
        </RouterView>
      </main>
      <AppMobileDock />
    </div>
  </div>
</template>

<style scoped lang="scss">
.app-shell {
  display: flex;
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--xunji-bg);
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 100vh;
  min-height: 100dvh;
}

.content {
  flex: 1;
  width: 100%;
  max-width: var(--xunji-content-max);
  padding: var(--xunji-space-6) max(var(--xunji-space-6), env(safe-area-inset-right))
    max(var(--xunji-space-6), env(safe-area-inset-bottom))
    max(var(--xunji-space-6), env(safe-area-inset-left));
  margin: 0 auto;
}

@media (max-width: 880px) {
  .sidebar-desktop {
    display: none;
  }

  .content {
    padding: var(--xunji-space-4) max(var(--xunji-space-4), env(safe-area-inset-right))
      calc(var(--xunji-dock-height) + env(safe-area-inset-bottom) + var(--xunji-space-4))
      max(var(--xunji-space-4), env(safe-area-inset-left));
  }
}
</style>
