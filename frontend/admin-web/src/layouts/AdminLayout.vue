<script setup lang="ts">
import { onMounted } from 'vue';
import { RouterView } from 'vue-router';

import AdminHeader from '@/components/AdminHeader.vue';
import AdminSidebar from '@/components/AdminSidebar.vue';
import { useAuthStore } from '@/stores/auth';

const auth = useAuthStore();

onMounted(async () => {
  if (auth.token && !auth.profile) {
    await auth.loadProfile().catch(() => {});
  }
});
</script>

<template>
  <div class="admin-shell">
    <AdminSidebar />
    <div class="main">
      <AdminHeader />
      <main class="content">
        <RouterView v-slot="{ Component, route }">
          <Transition name="fade-slide" mode="out-in">
            <component :is="Component" :key="route.fullPath" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped lang="scss">
.admin-shell {
  display: flex;
  min-height: 100vh;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.content {
  flex: 1;
  padding: 24px 28px;
  max-width: 1440px;
  width: 100%;
  margin: 0 auto;
}

@media (max-width: 880px) {
  .content {
    padding: 16px;
  }
}
</style>
