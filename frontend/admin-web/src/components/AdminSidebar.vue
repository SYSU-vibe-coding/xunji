<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import {
  Aim,
  Bell,
  ChatLineRound,
  Document,
  House,
  List,
  Medal,
  Promotion,
  User,
  Warning,
} from '@element-plus/icons-vue';

const route = useRoute();

const items = [
  { key: '/dashboard', label: '总览', icon: House },
  { key: '/certifications', label: '认证审批', icon: Medal },
  { key: '/reviews', label: '内容审核', icon: Document },
  { key: '/claim-appeals', label: '认领管理', icon: ChatLineRound },
  { key: '/reports', label: '举报处理', icon: Warning },
  { key: '/announcements', label: '公告管理', icon: Bell },
  { key: '/matches', label: '匹配任务', icon: Promotion },
  { key: '/operation-logs', label: '操作日志', icon: List },
  { key: '/users', label: '用户管理', icon: User },
];

const active = computed(() => {
  const exact = items.find((it) => it.key === route.path);
  if (exact) return exact.key;
  const matched = items
    .filter((it) => route.path.startsWith(it.key))
    .sort((a, b) => b.key.length - a.key.length)[0];
  return matched?.key ?? '/dashboard';
});
</script>

<template>
  <aside class="admin-sidebar">
    <div class="brand">
      <div class="logo"><el-icon :size="20" color="#fff"><Aim /></el-icon></div>
      <div class="brand-text">
        <strong>寻迹后台</strong>
        <small>Admin Console</small>
      </div>
    </div>

    <el-menu
      :default-active="active"
      router
      class="menu"
      background-color="transparent"
      text-color="var(--xunji-sidebar-text)"
      active-text-color="#ffffff"
    >
      <el-menu-item v-for="it in items" :key="it.key" :index="it.key">
        <el-icon><component :is="it.icon" /></el-icon>
        <template #title>{{ it.label }}</template>
      </el-menu-item>
    </el-menu>
  </aside>
</template>

<style scoped lang="scss">
.admin-sidebar {
  width: 232px;
  flex-shrink: 0;
  height: 100vh;
  background: var(--xunji-sidebar);
  display: flex;
  flex-direction: column;
  padding: 22px 14px;
  position: sticky;
  top: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 8px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);

  .logo {
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: linear-gradient(135deg, #14b8a6, #7c3aed);
    display: grid;
    place-items: center;
  }
  .brand-text {
    color: #fff;

    strong {
      display: block;
      font-weight: 700;
      font-size: 16px;
    }
    small {
      color: rgba(255, 255, 255, 0.6);
      font-size: 11px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }
  }
}

.menu {
  border-right: none;
  margin-top: 14px;
  background: transparent;

  :deep(.el-menu-item) {
    border-radius: 10px;
    margin: 4px 0;
    height: 44px;
    line-height: 44px;
  }
  :deep(.el-menu-item.is-active) {
    background: rgba(255, 255, 255, 0.12);
    font-weight: 600;
  }
  :deep(.el-menu-item:hover) {
    background: rgba(255, 255, 255, 0.06);
  }
}
</style>
