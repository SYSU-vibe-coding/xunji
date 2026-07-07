<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  Aim,
  Bell,
  ChatLineRound,
  Document,
  HomeFilled,
  Plus,
  Search,
  User,
} from '@element-plus/icons-vue';

import { useAuthStore } from '@/stores/auth';
import { useNotificationStore } from '@/stores/notification';
import { getInitial } from '@/utils/format';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const notice = useNotificationStore();

const navItems = [
  { key: 'home', label: '首页', icon: HomeFilled, route: '/' },
  { key: 'search', label: '检索', icon: Search, route: '/search' },
  { key: 'publish-lost', label: '发布失物', icon: Plus, route: '/publish/lost' },
  { key: 'publish-found', label: '发布招领', icon: Document, route: '/publish/found' },
  { key: 'matches', label: '匹配', icon: Aim, route: '/matches' },
  { key: 'my-claims', label: '我的认领', icon: ChatLineRound, route: '/claims' },
  { key: 'notifications', label: '消息', icon: Bell, route: '/notifications' },
  { key: 'profile', label: '我的', icon: User, route: '/profile' },
];

const activeKey = computed(() => {
  const exact = navItems.find((it) => it.route === route.path);
  if (exact) return exact.route;
  // 前缀匹配
  const matched = navItems
    .filter((it) => it.route !== '/' && route.path.startsWith(it.route))
    .sort((a, b) => b.route.length - a.route.length)[0];
  return matched?.route ?? '/';
});

function go(path: string) {
  void router.push(path);
}
</script>

<template>
  <aside class="app-sidebar">
    <div class="brand">
      <div class="logo"><el-icon :size="20" color="#fff"><Aim /></el-icon></div>
      <div>
        <strong>寻迹</strong>
        <small>Xunji</small>
      </div>
    </div>

    <el-menu
      class="nav"
      :default-active="activeKey"
      router
      background-color="transparent"
      text-color="var(--xunji-text)"
      active-text-color="var(--el-color-primary)"
    >
      <el-menu-item v-for="item in navItems" :key="item.key" :index="item.route">
        <el-icon><component :is="item.icon" /></el-icon>
        <template #title>
          <span class="menu-title-text">{{ item.label }}</span>
          <el-badge
            v-if="item.key === 'notifications' && notice.unreadTotal"
            :value="notice.unreadTotal"
            :max="99"
            class="menu-badge"
          />
        </template>
      </el-menu-item>
    </el-menu>

    <button class="profile-chip" type="button" @click="go('/profile')">
      <el-avatar :size="36" :src="auth.profile?.avatarUrl ?? undefined">
        {{ getInitial(auth.profile?.nickname) }}
      </el-avatar>
      <div class="info">
        <strong>{{ auth.displayName }}</strong>
        <small>信誉 {{ auth.profile?.creditScore ?? '—' }}</small>
      </div>
    </button>
  </aside>
</template>

<style scoped lang="scss">
.app-sidebar {
  width: 232px;
  flex-shrink: 0;
  background: var(--xunji-surface);
  border-right: 1px solid var(--xunji-border);
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  position: sticky;
  top: 0;
  height: 100vh;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px 12px;
  border-bottom: 1px solid var(--xunji-border);

  .logo {
    width: 38px;
    height: 38px;
    display: grid;
    place-items: center;
    background: var(--xunji-hero);
    border-radius: 12px;
  }

  strong {
    display: block;
    font-weight: 700;
    font-size: 16px;
  }
  small {
    color: var(--xunji-text-muted);
    font-size: 11px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }
}

.nav {
  border-right: none;
  flex: 1;
  background: transparent;

  :deep(.el-menu-item) {
    border-radius: 10px;
    margin: 4px 0;
    height: 44px;
    line-height: 44px;
  }
  :deep(.el-menu-item.is-active) {
    background: rgba(13, 79, 79, 0.08);
    font-weight: 600;
  }
  :deep(.el-menu-item:hover) {
    background: rgba(13, 79, 79, 0.05);
  }

  .menu-title-text {
    flex-shrink: 0;
  }

  .menu-badge {
    margin-left: 6px;
    :deep(.el-badge__content) {
      line-height: 18px;
    }
  }
}

.profile-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--xunji-bg);
  border: 1px solid var(--xunji-border);
  cursor: pointer;
  transition: background 0.18s;

  &:hover {
    background: rgba(13, 79, 79, 0.06);
  }

  .info {
    text-align: left;
    line-height: 1.3;
    strong {
      display: block;
      font-size: 14px;
      color: var(--xunji-text);
    }
    small {
      color: var(--xunji-text-muted);
      font-size: 12px;
    }
  }
}
</style>
