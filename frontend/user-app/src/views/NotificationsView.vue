<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Bell } from '@element-plus/icons-vue';

import AnnouncementPanel from '@/components/AnnouncementPanel.vue';
import EmptyState from '@/components/EmptyState.vue';
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '@/api/notification';
import { ApiError, isAuthApiError } from '@/api/http';
import { useNotificationStore } from '@/stores/notification';
import type { NotificationSummary } from '@xunji/shared';
import { noticeTypeLabels } from '@xunji/shared';
import { relativeTime } from '@/utils/format';
import { getNotificationTarget } from '@/utils/interaction';

type MessageTab = 'notifications' | 'announcements';

const route = useRoute();
const router = useRouter();
const noticeStore = useNotificationStore();

const list = ref<NotificationSummary[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const loading = ref(false);
const loadError = ref('');
const notificationsLoaded = ref(false);

const activeTab = computed<MessageTab>({
  get: () => (route.query.tab === 'announcements' ? 'announcements' : 'notifications'),
  set: (tab) => {
    if (tab === activeTab.value && route.query.tab === tab) return;
    void router.replace({ query: { ...route.query, tab } });
  },
});

async function load() {
  loading.value = true;
  loadError.value = '';
  try {
    const data = await listNotifications({ pageNo: page.value, pageSize });
    list.value = data.list;
    total.value = data.total;
  } catch (err) {
    if (isAuthApiError(err)) return;
    list.value = [];
    total.value = 0;
    loadError.value = err instanceof ApiError ? err.message : '消息加载失败，请稍后重试';
  } finally {
    loading.value = false;
    notificationsLoaded.value = true;
  }
}

async function handleClick(item: NotificationSummary) {
  if (!item.isRead) {
    try {
      await markNotificationRead(item.id);
      item.isRead = true;
      await noticeStore.refresh();
    } catch {
      /* ignore */
    }
  }
  const target = getNotificationTarget(item.relatedType, item.relatedId);
  if (target) void router.push(target);
}

async function handleMarkAll() {
  try {
    await markAllNotificationsRead();
    list.value.forEach((it) => (it.isRead = true));
    await noticeStore.refresh();
    ElMessage.success('已全部标记为已读');
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  }
}

watch(
  activeTab,
  (tab) => {
    if (tab === 'notifications' && !notificationsLoaded.value) void load();
  },
  { immediate: true },
);
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <span class="eyebrow">Messages</span>
        <h1>消息中心</h1>
        <p>通知与校园公告分类归档，重要动态一目了然</p>
      </div>
      <el-button
        v-if="activeTab === 'notifications'"
        type="primary"
        plain
        :disabled="!noticeStore.unreadTotal"
        @click="handleMarkAll"
      >
        全部标记为已读
      </el-button>
    </header>

    <el-tabs v-model="activeTab" class="message-tabs">
      <el-tab-pane label="通知" name="notifications">
        <section class="notification-panel" aria-label="通知列表" aria-live="polite">
          <el-skeleton v-if="loading" :rows="4" animated />
          <template v-else>
            <EmptyState
              v-if="loadError"
              title="通知加载失败"
              :description="loadError"
              action-text="重试"
              @action="load"
            />
            <el-card v-else-if="list.length" shadow="never" :body-style="{ padding: 0 }">
              <button
                v-for="n in list"
                :key="n.id"
                type="button"
                class="row"
                :class="{ unread: !n.isRead }"
                @click="handleClick(n)"
              >
                <span class="dot" aria-hidden="true" />
                <span class="body">
                  <span class="meta">
                    <el-tag size="small" effect="plain">{{ noticeTypeLabels[n.noticeType] }}</el-tag>
                    <time class="time" :datetime="n.createdAt">{{ relativeTime(n.createdAt) }}</time>
                  </span>
                  <strong>{{ n.title }}</strong>
                  <span v-if="n.content" class="content">{{ n.content }}</span>
                </span>
                <el-tag v-if="n.priority === 'HIGH'" type="danger" size="small">高优</el-tag>
              </button>
            </el-card>
            <EmptyState v-else title="暂无通知" description="认领、匹配与系统通知会显示在这里">
              <template #icon><Bell /></template>
            </EmptyState>

            <el-pagination
              v-if="total > pageSize"
              v-model:current-page="page"
              :page-size="pageSize"
              :total="total"
              layout="prev, pager, next"
              background
              class="pagination"
              aria-label="通知分页"
              @current-change="load"
            />
          </template>
        </section>
      </el-tab-pane>
      <el-tab-pane label="公告" name="announcements" lazy>
        <AnnouncementPanel />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;

  .eyebrow {
    color: var(--xunji-text-muted);
    font-size: 12px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }
  h1 {
    margin: 6px 0 4px;
    font-size: 22px;
  }
  p {
    margin: 0;
    color: var(--xunji-text-muted);
    font-size: 13px;
  }
}

.message-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 18px;
  }
  :deep(.el-tabs__item) {
    min-width: 72px;
    font-size: 15px;
  }
}

.notification-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.row {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 18px;
  border: none;
  border-bottom: 1px solid var(--xunji-border);
  background: transparent;
  color: inherit;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: background 0.18s;

  &:hover,
  &:focus-visible {
    background: rgba(13, 79, 79, 0.04);
  }
  &:focus-visible {
    outline: 2px solid var(--el-color-primary);
    outline-offset: -2px;
  }
  &:last-child {
    border-bottom: none;
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    margin-top: 8px;
    background: transparent;
  }
  &.unread .dot {
    background: var(--el-color-primary);
  }

  .body {
    min-width: 0;
    flex: 1;
    display: block;
    .meta {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
      .time {
        color: var(--xunji-text-muted);
        font-size: 12px;
      }
    }
    strong {
      display: block;
      font-size: 15px;
      font-weight: 600;
      color: var(--xunji-text);
    }
    .content {
      display: block;
      margin: 4px 0 0;
      color: var(--xunji-text-muted);
      font-size: 13px;
      line-height: 1.5;
    }
  }
}

.pagination {
  justify-content: center;
}

@media (max-width: 640px) {
  .page-header {
    align-items: flex-start;
    h1 {
      font-size: 20px;
    }
  }
  .row {
    gap: 10px;
    padding: 14px 12px;
  }
}
</style>
