<script setup lang="ts">
import { computed, ref } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { Bell, Document, HomeFilled, Plus, Search, User } from '@element-plus/icons-vue';

import { useNotificationStore } from '@/stores/notification';
import {
  isMobileNavActive,
  MOBILE_NAV_ORDER,
  type MobileNavKey,
} from '@/utils/navigation';

const route = useRoute();
const router = useRouter();
const noticeStore = useNotificationStore();

const itemByKey = {
  home: { key: 'home', label: '首页', icon: HomeFilled, to: '/' },
  search: { key: 'search', label: '检索', icon: Search, to: '/search' },
  publish: { key: 'publish', label: '发布', icon: Plus },
  notifications: { key: 'notifications', label: '消息', icon: Bell, to: '/notifications' },
  profile: { key: 'profile', label: '我的', icon: User, to: '/profile' },
} as const;

const items = MOBILE_NAV_ORDER.map((key) => itemByKey[key]);

const activePath = computed(() => route.path);
const sheetOpen = ref(false);

function isActive(key: MobileNavKey) {
  return isMobileNavActive(key, activePath.value);
}

function pickPublish(target: string) {
  sheetOpen.value = false;
  void router.push(target);
}
</script>

<template>
  <nav class="mobile-dock" aria-label="移动端主导航">
    <template v-for="item in items" :key="item.key">
      <button
        v-if="item.key === 'publish'"
        type="button"
        :class="['dock-item', 'accent', { active: isActive(item.key) }]"
        aria-label="发布信息"
        :aria-current="isActive(item.key) ? 'page' : undefined"
        @click="sheetOpen = true"
      >
        <span class="accent-icon"><el-icon :size="23"><Plus /></el-icon></span>
        <span>发布</span>
      </button>
      <RouterLink
        v-else
        :to="item.to"
        :class="['dock-item', { active: isActive(item.key) }]"
        :aria-label="
          item.key === 'notifications' && noticeStore.unreadTotal
            ? `${item.label}，${noticeStore.unreadTotal} 条未读`
            : item.label
        "
        :aria-current="isActive(item.key) ? 'page' : undefined"
      >
        <el-badge
          v-if="item.key === 'notifications'"
          :value="noticeStore.unreadTotal"
          :hidden="!noticeStore.unreadTotal"
          :max="99"
          class="dock-badge"
          aria-hidden="true"
        >
          <el-icon :size="20"><Bell /></el-icon>
        </el-badge>
        <el-icon v-else :size="20"><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </RouterLink>
    </template>
  </nav>

  <el-drawer
    v-model="sheetOpen"
    class="publish-drawer"
    direction="btt"
    size="auto"
    title="选择发布类型"
    append-to-body
    lock-scroll
    close-on-press-escape
    trap-focus
    destroy-on-close
  >
    <div class="publish-sheet">
      <p>想要发布什么？</p>
      <button type="button" class="sheet-action lost" @click="pickPublish('/publish/lost')">
        <span class="action-icon"><el-icon :size="22"><Search /></el-icon></span>
        <span class="text">
          <strong>发布失物</strong>
          <small>东西丢了，希望大家帮忙留意</small>
        </span>
      </button>
      <button type="button" class="sheet-action found" @click="pickPublish('/publish/found')">
        <span class="action-icon"><el-icon :size="22"><Document /></el-icon></span>
        <span class="text">
          <strong>发布招领</strong>
          <small>捡到东西，登记并等待失主认领</small>
        </span>
      </button>
    </div>
  </el-drawer>
</template>

<style scoped lang="scss">
.mobile-dock {
  display: none;
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: var(--xunji-z-dock);
  background: var(--xunji-surface);
  border-top: 1px solid var(--xunji-border);
  padding: 6px 8px calc(env(safe-area-inset-bottom) + 6px);
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.dock-item {
  min-width: 0;
  min-height: 52px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 5px 2px;
  border: none;
  background: transparent;
  color: var(--xunji-text-muted);
  font-family: inherit;
  font-size: 11px;
  line-height: 1.2;
  text-decoration: none;
  cursor: pointer;
  border-radius: 12px;

  &.active {
    color: var(--el-color-primary);
    font-weight: 600;
  }

  &.accent {
    color: var(--el-color-primary);
  }

  &:focus-visible {
    outline: 2px solid var(--el-color-primary);
    outline-offset: -2px;
  }
}

.accent-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  margin-top: -23px;
  color: #fff;
  border: 3px solid var(--xunji-surface);
  border-radius: 17px;
  background: var(--xunji-hero);
  box-shadow: 0 8px 20px rgba(13, 79, 79, 0.3);
}

.dock-item.active .accent-icon {
  box-shadow: 0 0 0 2px rgba(20, 184, 166, 0.24), 0 8px 20px rgba(13, 79, 79, 0.3);
}

:deep(.dock-badge .el-badge__content) {
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-width: 1px;
  font-size: 10px;
  line-height: 14px;
  transform: translate(75%, -45%);
}

@media (max-width: 880px) {
  .mobile-dock {
    display: grid;
  }
}

.publish-sheet {
  max-width: 520px;
  margin: 0 auto;
  padding-bottom: env(safe-area-inset-bottom);
  display: flex;
  flex-direction: column;
  gap: 10px;
  p {
    margin: -4px 0 4px;
    color: var(--xunji-text-muted);
    font-size: 13px;
  }
}

.sheet-action {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px;
  border: 1px solid var(--xunji-border);
  background: var(--xunji-bg);
  border-radius: 14px;
  color: inherit;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;

  .action-icon {
    width: 40px;
    height: 40px;
    display: grid;
    flex: 0 0 40px;
    place-items: center;
    border-radius: 12px;
    background: rgba(13, 79, 79, 0.07);
  }
  .text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    strong {
      font-size: 15px;
      color: var(--xunji-text);
    }
    small {
      font-size: 12px;
      color: var(--xunji-text-muted);
    }
  }

  &:hover,
  &:focus-visible {
    background: rgba(13, 79, 79, 0.05);
    border-color: rgba(13, 79, 79, 0.25);
  }
  &:focus-visible {
    outline: 2px solid var(--el-color-primary);
    outline-offset: 2px;
  }
  &:active {
    background: rgba(13, 79, 79, 0.1);
  }

  &.lost .el-icon {
    color: #0d4f4f;
  }
  &.found .el-icon {
    color: #b45309;
  }
}

:deep(.publish-drawer) {
  max-height: min(420px, 80vh);
  border-radius: 20px 20px 0 0;
  .el-drawer__header {
    margin-bottom: 0;
    padding-bottom: 12px;
    color: var(--xunji-text);
    font-weight: 650;
  }
  .el-drawer__body {
    padding-top: 4px;
  }
}
</style>
