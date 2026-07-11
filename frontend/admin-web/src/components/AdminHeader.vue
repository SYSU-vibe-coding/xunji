<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { SwitchButton, User } from '@element-plus/icons-vue';

import { useAuthStore } from '@/stores/auth';
import { getInitial } from '@/utils/format';

const route = useRoute();
const auth = useAuthStore();

const titleMap: Record<string, string> = {
  '/dashboard': '总览',
  '/certifications': '认证审批',
  '/reviews': '内容审核',
  '/claim-appeals': '认领申诉',
  '/reports': '举报处理',
  '/announcements': '公告管理',
  '/matches': '匹配任务',
  '/operation-logs': '操作日志',
  '/users': '用户管理',
};

const title = computed(() => {
  const matched = Object.keys(titleMap)
    .filter((k) => route.path.startsWith(k))
    .sort((a, b) => b.length - a.length)[0];
  return matched ? titleMap[matched] : '寻迹管理后台';
});

function handleCommand(cmd: string) {
  if (cmd === 'logout') auth.logout();
}
</script>

<template>
  <header class="admin-header">
    <div class="title">
      <span class="eyebrow">寻迹管理后台</span>
      <h1>{{ title }}</h1>
    </div>

    <div class="actions">
      <el-dropdown trigger="click" @command="handleCommand">
        <div class="me">
          <el-avatar :size="32" class="avatar">{{ getInitial(auth.profile?.nickname) }}</el-avatar>
          <span>{{ auth.displayName }}</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              <el-icon><User /></el-icon>{{ auth.profile?.phone ?? '—' }}
            </el-dropdown-item>
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
.admin-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  background: var(--xunji-surface);
  border-bottom: 1px solid var(--xunji-border);
  position: sticky;
  top: 0;
  z-index: 10;
}

.title {
  .eyebrow {
    color: var(--xunji-text-muted);
    font-size: 12px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }
  h1 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
  }
}

.me {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.18s;

  &:hover {
    background: var(--xunji-bg);
  }

  .avatar {
    background: var(--xunji-primary);
    color: #fff;
    font-weight: 600;
  }

  span {
    font-size: 14px;
    font-weight: 500;
  }
}
</style>
