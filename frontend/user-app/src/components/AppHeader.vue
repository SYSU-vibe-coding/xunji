<script setup lang="ts">
import { useRouter } from 'vue-router';
import { Aim, Bell, SwitchButton, User } from '@element-plus/icons-vue';

import { useAuthStore } from '@/stores/auth';
import { useNotificationStore } from '@/stores/notification';
import { getInitial } from '@/utils/format';

const router = useRouter();
const auth = useAuthStore();
const notice = useNotificationStore();

function handleCommand(cmd: string) {
  if (cmd === 'profile') void router.push('/profile');
  if (cmd === 'logout') auth.logout();
}
</script>

<template>
  <header class="app-header">
    <div class="brand-mobile">
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
