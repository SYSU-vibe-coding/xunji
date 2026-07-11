<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Aim, ArrowDown, ArrowLeft, Bell, SwitchButton, User } from '@element-plus/icons-vue';

import { useAuthStore } from '@/stores/auth';
import { useNotificationStore } from '@/stores/notification';
import { getInitial } from '@/utils/format';

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const notice = useNotificationStore();

// 主 tab 由 router meta.tab 标记，不显示返回按钮
const showBack = computed(() => !route.meta?.tab);

function handleCommand(cmd: string) {
  if (cmd === 'profile') void router.push('/profile');
  if (cmd === 'logout') auth.logout();
}

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    void router.push('/');
  }
}
</script>

<template>
  <header class="app-header">
    <button
      v-if="showBack"
      type="button"
      class="back-btn"
      aria-label="返回"
      @click="goBack"
    >
      <el-icon :size="18"><ArrowLeft /></el-icon>
      <span>返回</span>
    </button>
    <div v-else class="brand-mobile">
      <div class="logo"><el-icon :size="18" color="#fff"><Aim /></el-icon></div>
      <strong>寻迹</strong>
    </div>

    <div class="actions">
      <el-badge :value="notice.unreadTotal" :hidden="!notice.unreadTotal" :max="99">
        <el-button
          class="header-icon-button"
          circle
          plain
          :aria-label="
            notice.unreadTotal ? `查看消息通知，${notice.unreadTotal} 条未读` : '查看消息通知'
          "
          @click="router.push('/notifications')"
        >
          <el-icon><Bell /></el-icon>
        </el-button>
      </el-badge>

      <el-dropdown trigger="click" @command="handleCommand">
        <button type="button" class="account-trigger" aria-label="打开账户菜单">
          <el-avatar :size="34" :src="auth.profile?.avatarUrl ?? undefined" class="avatar">
            {{ getInitial(auth.profile?.nickname) }}
          </el-avatar>
          <span class="account-name">{{ auth.displayName }}</span>
          <el-icon class="account-arrow"><ArrowDown /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile"><el-icon><User /></el-icon>个人中心</el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<style scoped lang="scss">
.app-header {
  position: sticky;
  top: 0;
  z-index: var(--xunji-z-header);
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  height: calc(var(--xunji-header-height) + env(safe-area-inset-top));
  padding: env(safe-area-inset-top) max(var(--xunji-space-5), env(safe-area-inset-right)) 0
    max(var(--xunji-space-5), env(safe-area-inset-left));
  background: var(--xunji-surface);
  border-bottom: 1px solid var(--xunji-border);
  box-shadow: var(--xunji-shadow-sm);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: var(--xunji-touch-target);
  min-height: var(--xunji-touch-target);
  gap: var(--xunji-space-1);
  padding: 0 var(--xunji-space-3) 0 var(--xunji-space-2);
  background: transparent;
  border: 1px solid var(--xunji-border);
  border-radius: var(--xunji-radius-pill);
  color: var(--xunji-text);
  font-size: var(--xunji-font-size-sm);
  font-weight: var(--xunji-font-weight-medium);
  cursor: pointer;
  transition:
    color var(--xunji-motion-fast) var(--xunji-ease-standard),
    background var(--xunji-motion-fast) var(--xunji-ease-standard),
    border-color var(--xunji-motion-fast) var(--xunji-ease-standard);

  &:hover {
    color: var(--xunji-primary);
    background: var(--xunji-primary-soft);
    border-color: var(--xunji-primary-light-5);
  }

  &:active {
    background: var(--xunji-primary-light-8);
  }

  &:focus-visible {
    outline: 3px solid var(--xunji-focus-ring);
    outline-offset: 2px;
  }
}

.brand-mobile {
  display: none;
  align-items: center;
  gap: var(--xunji-space-2);

  .logo {
    width: 32px;
    height: 32px;
    display: grid;
    place-items: center;
    background: var(--xunji-primary);
    border-radius: var(--xunji-radius-sm);
    box-shadow: var(--xunji-shadow-sm);
  }

  strong {
    color: var(--xunji-text-strong);
    font-size: var(--xunji-font-size-base);
    font-weight: var(--xunji-font-weight-bold);
    letter-spacing: 0.04em;
  }
}

.actions {
  display: flex;
  align-items: center;
  gap: var(--xunji-space-2);
  margin-left: auto;
}

:deep(.header-icon-button.el-button) {
  width: var(--xunji-touch-target);
  height: var(--xunji-touch-target);
  color: var(--xunji-text-muted);
  background: var(--xunji-surface);
  border-color: var(--xunji-border);

  &:hover {
    color: var(--xunji-primary);
    background: var(--xunji-primary-soft);
    border-color: var(--xunji-primary-light-5);
  }

  &:focus-visible {
    outline: 3px solid var(--xunji-focus-ring);
    outline-offset: 2px;
  }
}

.account-trigger {
  display: inline-flex;
  align-items: center;
  min-height: var(--xunji-touch-target);
  gap: var(--xunji-space-2);
  padding: 4px var(--xunji-space-2) 4px 5px;
  color: var(--xunji-text);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--xunji-radius-pill);
  cursor: pointer;
  transition:
    background var(--xunji-motion-fast) var(--xunji-ease-standard),
    border-color var(--xunji-motion-fast) var(--xunji-ease-standard);

  &:hover,
  &[aria-expanded='true'] {
    background: var(--xunji-surface-hover);
    border-color: var(--xunji-border);
  }

  &:focus-visible {
    outline: 3px solid var(--xunji-focus-ring);
    outline-offset: 2px;
  }
}

.avatar {
  color: var(--xunji-text-inverse);
  background: var(--xunji-primary);
  font-weight: var(--xunji-font-weight-semibold);
}

.account-name {
  max-width: 120px;
  overflow: hidden;
  font-size: var(--xunji-font-size-sm);
  font-weight: var(--xunji-font-weight-medium);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-arrow {
  color: var(--xunji-text-muted);
  font-size: 12px;
}

@media (max-width: 880px) {
  .app-header {
    height: calc(var(--xunji-header-height-mobile) + env(safe-area-inset-top));
    padding: env(safe-area-inset-top) max(var(--xunji-space-4), env(safe-area-inset-right)) 0
      max(var(--xunji-space-4), env(safe-area-inset-left));
  }

  .brand-mobile {
    display: flex;
  }

  .actions {
    display: none;
  }
}
</style>
