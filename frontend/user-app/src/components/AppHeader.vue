<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Aim, ArrowLeft, Bell, SwitchButton, User } from '@element-plus/icons-vue';

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
        <el-button circle plain size="default" @click="router.push('/notifications')">
          <el-icon><Bell /></el-icon>
        </el-button>
      </el-badge>

      <el-dropdown trigger="click" @command="handleCommand">
        <el-avatar :size="34" :src="auth.profile?.avatarUrl ?? undefined" class="avatar">
          {{ getInitial(auth.profile?.nickname) }}
        </el-avatar>
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
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--xunji-surface);
  border-bottom: 1px solid var(--xunji-border);
  position: sticky;
  top: 0;
  z-index: 10;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px 6px 8px;
  background: transparent;
  border: 1px solid var(--xunji-border);
  border-radius: 999px;
  color: var(--xunji-text);
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;

  &:hover {
    background: rgba(13, 79, 79, 0.06);
    border-color: rgba(13, 79, 79, 0.3);
  }
  &:active {
    background: rgba(13, 79, 79, 0.1);
  }
}

.brand-mobile {
  display: none;
  align-items: center;
  gap: 8px;

  .logo {
    width: 30px;
    height: 30px;
    border-radius: 9px;
    display: grid;
    place-items: center;
    background: var(--xunji-hero);
  }
  strong {
    font-weight: 700;
    font-size: 15px;
  }
}

.actions {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-left: auto;
}

.avatar {
  cursor: pointer;
  background: var(--xunji-hero);
  color: #fff;
  font-weight: 600;
}

@media (max-width: 880px) {
  .brand-mobile {
    display: flex;
  }
}
</style>
