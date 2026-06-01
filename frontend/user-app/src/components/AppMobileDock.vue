<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Bell, HomeFilled, Plus, Search, User } from '@element-plus/icons-vue';

const route = useRoute();
const router = useRouter();

const items = [
  { key: 'home', label: '首页', icon: HomeFilled, route: '/' },
  { key: 'search', label: '检索', icon: Search, route: '/search' },
  { key: 'publish', label: '发布', icon: Plus, route: '/publish/lost', accent: true },
  { key: 'notifications', label: '消息', icon: Bell, route: '/notifications' },
  { key: 'profile', label: '我的', icon: User, route: '/profile' },
];

const activePath = computed(() => route.path);

function go(path: string) {
  if (path !== activePath.value) void router.push(path);
}

function isActive(path: string) {
  return path === '/' ? activePath.value === '/' : activePath.value.startsWith(path);
}
</script>

<template>
  <nav class="mobile-dock">
    <button
      v-for="item in items"
      :key="item.key"
      type="button"
      :class="['dock-item', { active: isActive(item.route), accent: item.accent }]"
      @click="go(item.route)"
    >
      <el-icon :size="item.accent ? 22 : 19"><component :is="item.icon" /></el-icon>
      <span v-if="!item.accent">{{ item.label }}</span>
    </button>
  </nav>
</template>

<style scoped lang="scss">
.mobile-dock {
  display: none;
  position: sticky;
  bottom: 0;
  z-index: 12;
  background: var(--xunji-surface);
  border-top: 1px solid var(--xunji-border);
  padding: 6px 8px calc(env(safe-area-inset-bottom) + 6px);
  justify-content: space-around;
}

.dock-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 8px 6px;
  border: none;
  background: transparent;
  color: var(--xunji-text-muted);
  font-size: 11px;
  cursor: pointer;
  border-radius: 10px;

  &.active {
    color: var(--el-color-primary);
    font-weight: 600;
  }

  &.accent {
    margin: -16px 6px 0;
    background: var(--xunji-hero);
    color: #fff;
    width: 52px;
    height: 52px;
    flex: 0 0 52px;
    border-radius: 16px;
    box-shadow: 0 8px 22px rgba(13, 79, 79, 0.35);
  }
}

@media (max-width: 880px) {
  .mobile-dock {
    display: flex;
  }
}
</style>
