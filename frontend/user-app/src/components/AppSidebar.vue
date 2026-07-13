<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  Aim,
  Bell,
  ChatLineRound,
  Document,
  HomeFilled,
  Plus,
  Search,
} from '@element-plus/icons-vue';

import { useAuthStore } from '@/stores/auth';
import { useNotificationStore } from '@/stores/notification';
import { getInitial } from '@/utils/format';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const notice = useNotificationStore();
const publishOpen = ref(false);

const mainNavItems = [
  { key: 'home', label: '首页', icon: HomeFilled, route: '/' },
  { key: 'search', label: '检索', icon: Search, route: '/search' },
  { key: 'notifications', label: '消息', icon: Bell, route: '/notifications' },
];

const businessNavItems = [
  { key: 'matches', label: '匹配', icon: Aim, route: '/matches' },
  { key: 'my-claims', label: '我的认领', icon: ChatLineRound, route: '/claims' },
];

const navItems = [...mainNavItems, ...businessNavItems];
const isPublishing = computed(() => route.name === 'publish-lost' || route.name === 'publish-found');
const isProfileActive = computed(() => route.path.startsWith('/profile'));

const activeKey = computed(() => {
  if (route.name === 'announcement-detail') return '/notifications';
  const exact = navItems.find((it) => it.route === route.path);
  if (exact) return exact.route;
  // 前缀匹配
  const matched = navItems
    .filter((it) => it.route !== '/' && route.path.startsWith(it.route))
    .sort((a, b) => b.route.length - a.route.length)[0];
  return matched?.route ?? '';
});

function go(path: string) {
  void router.push(path);
}

function pickPublish(path: string) {
  publishOpen.value = false;
  void router.push(path);
}
</script>

<template>
  <aside class="app-sidebar">
    <div class="brand">
      <div class="logo"><el-icon :size="20" color="#fff"><Aim /></el-icon></div>
      <div>
        <strong>寻迹</strong>
        <small>校园失物招领</small>
      </div>
    </div>

    <el-popover
      v-model:visible="publishOpen"
      placement="right-start"
      trigger="click"
      :width="276"
      popper-class="publish-popover"
    >
      <template #reference>
        <button
          type="button"
          :class="['publish-button', { active: isPublishing }]"
          aria-label="选择发布失物或招领"
          aria-haspopup="dialog"
          :aria-expanded="publishOpen"
        >
          <span class="publish-icon"><el-icon :size="19"><Plus /></el-icon></span>
          <span>发布信息</span>
        </button>
      </template>

      <div class="publish-picker" role="dialog" aria-label="选择发布类型">
        <strong>选择发布类型</strong>
        <p>根据物品当前状态创建信息</p>
        <button type="button" aria-label="发布失物信息" @click="pickPublish('/publish/lost')">
          <span class="picker-icon lost"><el-icon :size="19"><Search /></el-icon></span>
          <span><b>我丢了物品</b><small>发布失物，寻找线索</small></span>
        </button>
        <button type="button" aria-label="发布招领信息" @click="pickPublish('/publish/found')">
          <span class="picker-icon found"><el-icon :size="19"><Document /></el-icon></span>
          <span><b>我捡到物品</b><small>发布招领，等待失主</small></span>
        </button>
      </div>
    </el-popover>

    <div class="nav-scroll">
      <el-menu
        class="nav"
        :default-active="activeKey"
        router
        aria-label="用户端导航"
        background-color="transparent"
        text-color="var(--xunji-text)"
        active-text-color="var(--el-color-primary)"
      >
        <el-menu-item-group title="主导航">
          <el-menu-item v-for="item in mainNavItems" :key="item.key" :index="item.route">
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
        </el-menu-item-group>

        <el-menu-item-group title="业务快捷入口">
          <el-menu-item v-for="item in businessNavItems" :key="item.key" :index="item.route">
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>{{ item.label }}</template>
          </el-menu-item>
        </el-menu-item-group>
      </el-menu>
    </div>

    <button
      :class="['profile-chip', { active: isProfileActive }]"
      type="button"
      aria-label="打开个人中心"
      @click="go('/profile')"
    >
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
  position: sticky;
  top: 0;
  z-index: var(--xunji-z-sidebar);
  width: calc(var(--xunji-sidebar-width) + env(safe-area-inset-left));
  height: 100vh;
  height: 100dvh;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--xunji-space-4);
  padding: calc(var(--xunji-space-5) + env(safe-area-inset-top)) var(--xunji-space-4)
    calc(var(--xunji-space-4) + env(safe-area-inset-bottom))
    calc(var(--xunji-space-4) + env(safe-area-inset-left));
  overflow-y: auto;
  overscroll-behavior: contain;
  background: var(--xunji-surface);
  border-right: 1px solid var(--xunji-border);
  box-shadow: 1px 0 0 rgba(12, 30, 27, 0.02);
}

.brand {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: var(--xunji-space-3);
  padding: 2px var(--xunji-space-2) var(--xunji-space-2);

  .logo {
    width: 40px;
    height: 40px;
    flex: 0 0 40px;
    display: grid;
    place-items: center;
    background: var(--xunji-primary);
    border-radius: var(--xunji-radius);
    box-shadow: var(--xunji-shadow-sm);
  }

  strong {
    display: block;
    color: var(--xunji-text-strong);
    font-size: 17px;
    font-weight: var(--xunji-font-weight-bold);
    letter-spacing: 0.08em;
  }

  small {
    color: var(--xunji-text-muted);
    font-size: 10px;
    letter-spacing: 0.04em;
  }
}

.publish-button {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  gap: var(--xunji-space-2);
  padding: 0 var(--xunji-space-4);
  color: var(--xunji-text-inverse);
  background: var(--xunji-primary);
  border: 1px solid var(--xunji-primary);
  border-radius: var(--xunji-radius);
  box-shadow: 0 7px 18px rgba(13, 79, 79, 0.2);
  font-weight: var(--xunji-font-weight-semibold);
  cursor: pointer;
  transition:
    background var(--xunji-motion-fast) var(--xunji-ease-standard),
    box-shadow var(--xunji-motion-fast) var(--xunji-ease-standard),
    transform var(--xunji-motion-fast) var(--xunji-ease-standard);

  &:hover {
    background: var(--xunji-primary-hover);
    box-shadow: 0 9px 22px rgba(13, 79, 79, 0.24);
    transform: translateY(-1px);
  }

  &:active {
    background: var(--xunji-primary-dark);
    box-shadow: 0 4px 12px rgba(13, 79, 79, 0.18);
    transform: translateY(0);
  }

  &.active {
    box-shadow: 0 0 0 3px var(--xunji-focus-ring), 0 7px 18px rgba(13, 79, 79, 0.2);
  }

  &:focus-visible {
    outline: 3px solid var(--xunji-focus-ring);
    outline-offset: 2px;
  }
}

.publish-icon {
  display: grid;
  place-items: center;
}

.nav-scroll {
  flex: 1 0 auto;
  min-height: 0;
}

.nav {
  border-right: none;
  background: transparent;

  :deep(.el-menu-item-group__title) {
    height: auto;
    padding: var(--xunji-space-3) var(--xunji-space-3) var(--xunji-space-1) !important;
    color: var(--xunji-text-subtle);
    font-size: 11px;
    font-weight: var(--xunji-font-weight-semibold);
    line-height: var(--xunji-line-height-tight);
    letter-spacing: 0.08em;
  }

  :deep(.el-menu-item) {
    height: var(--xunji-touch-target);
    margin: 2px 0;
    padding: 0 var(--xunji-space-3) !important;
    border-radius: var(--xunji-radius-sm);
    line-height: var(--xunji-touch-target);
    transition:
      color var(--xunji-motion-fast) var(--xunji-ease-standard),
      background var(--xunji-motion-fast) var(--xunji-ease-standard);
  }

  :deep(.el-menu-item.is-active) {
    background: var(--xunji-primary-soft);
    font-weight: var(--xunji-font-weight-semibold);
  }

  :deep(.el-menu-item:hover) {
    background: var(--xunji-surface-subtle);
  }

  :deep(.el-menu-item:focus-visible) {
    outline: 3px solid var(--xunji-focus-ring);
    outline-offset: -2px;
  }

  .menu-title-text {
    flex-shrink: 0;
  }

  .menu-badge {
    display: inline-flex;
    flex-shrink: 0;
    align-items: center;
    margin-left: auto;

    :deep(.el-badge__content) {
      position: static;
      transform: none;
      line-height: 18px;
    }
  }
}

.profile-chip {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  min-height: 58px;
  gap: var(--xunji-space-3);
  margin-top: auto;
  padding: var(--xunji-space-2) var(--xunji-space-3);
  background: var(--xunji-surface-hover);
  border: 1px solid var(--xunji-border);
  border-radius: var(--xunji-radius);
  cursor: pointer;
  transition:
    background var(--xunji-motion-fast) var(--xunji-ease-standard),
    border-color var(--xunji-motion-fast) var(--xunji-ease-standard);

  &:hover {
    background: var(--xunji-primary-soft);
    border-color: var(--xunji-primary-light-5);
  }

  &.active {
    background: var(--xunji-primary-soft);
    border-color: var(--xunji-primary-light-5);
  }

  &:focus-visible {
    outline: 3px solid var(--xunji-focus-ring);
    outline-offset: 2px;
  }

  :deep(.el-avatar) {
    color: var(--xunji-text-inverse);
    background: var(--xunji-primary);
  }

  .info {
    min-width: 0;
    text-align: left;
    line-height: var(--xunji-line-height-tight);

    strong {
      display: block;
      overflow: hidden;
      color: var(--xunji-text);
      font-size: var(--xunji-font-size-sm);
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    small {
      color: var(--xunji-text-muted);
      font-size: var(--xunji-font-size-xs);
    }
  }
}

.publish-picker {
  color: var(--xunji-text);

  > strong {
    display: block;
    color: var(--xunji-text-strong);
    font-size: var(--xunji-font-size-base);
  }

  > p {
    margin: 2px 0 var(--xunji-space-3);
    color: var(--xunji-text-muted);
    font-size: var(--xunji-font-size-xs);
  }

  > button {
    width: 100%;
    min-height: 62px;
    display: flex;
    align-items: center;
    gap: var(--xunji-space-3);
    margin-top: var(--xunji-space-2);
    padding: var(--xunji-space-2) var(--xunji-space-3);
    color: var(--xunji-text);
    background: var(--xunji-surface-hover);
    border: 1px solid var(--xunji-border);
    border-radius: var(--xunji-radius-sm);
    text-align: left;
    cursor: pointer;
    transition:
      background var(--xunji-motion-fast) var(--xunji-ease-standard),
      border-color var(--xunji-motion-fast) var(--xunji-ease-standard);

    &:hover {
      background: var(--xunji-primary-soft);
      border-color: var(--xunji-primary-light-5);
    }

    &:focus-visible {
      outline: 3px solid var(--xunji-focus-ring);
      outline-offset: 2px;
    }

    > span:last-child {
      display: flex;
      flex-direction: column;
    }

    b {
      color: var(--xunji-text-strong);
      font-size: var(--xunji-font-size-sm);
      font-weight: var(--xunji-font-weight-semibold);
    }

    small {
      margin-top: 2px;
      color: var(--xunji-text-muted);
      font-size: var(--xunji-font-size-xs);
    }
  }
}

.picker-icon {
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  display: grid;
  place-items: center;
  border-radius: var(--xunji-radius-sm);

  &.lost {
    color: var(--xunji-primary);
    background: var(--xunji-primary-soft);
  }

  &.found {
    color: var(--xunji-warning);
    background: var(--xunji-warning-soft);
  }
}

:global(.publish-popover.el-popper) {
  padding: var(--xunji-space-4) !important;
  border: 1px solid var(--xunji-border) !important;
  border-radius: var(--xunji-radius) !important;
  box-shadow: var(--xunji-shadow) !important;
}
</style>
