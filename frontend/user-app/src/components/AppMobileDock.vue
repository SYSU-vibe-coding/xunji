<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Bell, Document, HomeFilled, Plus, Search, User } from '@element-plus/icons-vue';

const route = useRoute();
const router = useRouter();

const items = [
  { key: 'home', label: '首页', icon: HomeFilled, route: '/' },
  { key: 'search', label: '检索', icon: Search, route: '/search' },
  { key: 'publish', label: '发布', icon: Plus, route: '__publish__', accent: true },
  { key: 'notifications', label: '消息', icon: Bell, route: '/notifications' },
  { key: 'profile', label: '我的', icon: User, route: '/profile' },
];

const activePath = computed(() => route.path);
const sheetOpen = ref(false);

function handleClick(target: string) {
  if (target === '__publish__') {
    sheetOpen.value = true;
    return;
  }
  if (target !== activePath.value) void router.push(target);
}

function isActive(path: string) {
  if (path === '__publish__') {
    // 发布页两个路径都点亮加号
    return activePath.value.startsWith('/publish/');
  }
  return path === '/' ? activePath.value === '/' : activePath.value.startsWith(path);
}

function pickPublish(target: string) {
  sheetOpen.value = false;
  void router.push(target);
}
</script>

<template>
  <nav class="mobile-dock">
    <button
      v-for="item in items"
      :key="item.key"
      type="button"
      :class="['dock-item', { active: isActive(item.route), accent: item.accent }]"
      @click="handleClick(item.route)"
    >
      <el-icon :size="item.accent ? 22 : 19"><component :is="item.icon" /></el-icon>
      <span v-if="!item.accent">{{ item.label }}</span>
    </button>
  </nav>

  <Teleport to="body">
    <Transition name="sheet-fade">
      <div v-if="sheetOpen" class="sheet-mask" @click.self="sheetOpen = false">
        <div class="sheet" role="dialog" aria-label="选择发布类型">
          <div class="sheet-handle" />
          <div class="sheet-title">想要发布什么？</div>
          <button type="button" class="sheet-action lost" @click="pickPublish('/publish/lost')">
            <el-icon :size="22"><Search /></el-icon>
            <div class="text">
              <strong>发布失物</strong>
              <small>东西丢了，希望大家帮忙留意</small>
            </div>
          </button>
          <button type="button" class="sheet-action found" @click="pickPublish('/publish/found')">
            <el-icon :size="22"><Document /></el-icon>
            <div class="text">
              <strong>发布招领</strong>
              <small>捡到东西，登记并等待失主认领</small>
            </div>
          </button>
          <button type="button" class="sheet-cancel" @click="sheetOpen = false">取消</button>
        </div>
      </div>
    </Transition>
  </Teleport>
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

// ---- bottom sheet ----
.sheet-mask {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.sheet {
  width: 100%;
  max-width: 480px;
  background: var(--xunji-surface);
  border-radius: 18px 18px 0 0;
  padding: 10px 16px calc(env(safe-area-inset-bottom) + 16px);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sheet-handle {
  width: 40px;
  height: 4px;
  border-radius: 4px;
  background: var(--xunji-border);
  margin: 4px auto 6px;
}

.sheet-title {
  font-size: 14px;
  color: var(--xunji-text-muted);
  text-align: center;
  margin-bottom: 4px;
}

.sheet-action {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 14px;
  border: 1px solid var(--xunji-border);
  background: var(--xunji-bg);
  border-radius: 14px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;

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

  &:hover {
    background: rgba(13, 79, 79, 0.05);
    border-color: rgba(13, 79, 79, 0.25);
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

.sheet-cancel {
  margin-top: 4px;
  padding: 12px;
  border: none;
  background: transparent;
  color: var(--xunji-text-muted);
  font-size: 14px;
  border-top: 1px solid var(--xunji-border);
  cursor: pointer;
}

.sheet-fade-enter-active,
.sheet-fade-leave-active {
  transition: opacity 0.18s ease;
  .sheet {
    transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1);
  }
}
.sheet-fade-enter-from,
.sheet-fade-leave-to {
  opacity: 0;
  .sheet {
    transform: translateY(100%);
  }
}
</style>
