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

// 路由切换时刷新未读数（避免在通知页停留太久 dock 角标过期）
watch(
  () => route.fullPath,
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
            <component :is="Component" :key="r.fullPath" />
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
  background: var(--xunji-bg);
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.content {
  flex: 1;
  padding: 24px;
  max-width: 1280px;
  width: 100%;
  margin: 0 auto;
}

@media (max-width: 880px) {
  .sidebar-desktop {
    display: none;
  }
  .content {
    padding: 16px;
  }
}
</style>
