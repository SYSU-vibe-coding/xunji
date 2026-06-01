<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Bell } from '@element-plus/icons-vue';

import EmptyState from '@/components/EmptyState.vue';
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '@/api/notification';
import { ApiError } from '@/api/http';
import { useNotificationStore } from '@/stores/notification';
import {
  type NotificationSummary,
  noticeTypeLabels,
} from '@xunji/shared';
import { relativeTime } from '@/utils/format';

const router = useRouter();
const noticeStore = useNotificationStore();

const list = ref<NotificationSummary[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const loading = ref(true);

async function load() {
  loading.value = true;
  try {
    const data = await listNotifications({ pageNo: page.value, pageSize });
    list.value = data.list;
    total.value = data.total;
  } catch (err) {
    if (err instanceof ApiError && err.code === 40002) return;
    list.value = [];
  } finally {
    loading.value = false;
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
  if (item.relatedType === 'CLAIM' && item.relatedId) {
    void router.push(`/claims/${item.relatedId}`);
  } else if (item.relatedType === 'FOUND' && item.relatedId) {
    void router.push(`/items/found/${item.relatedId}`);
  } else if (item.relatedType === 'LOST' && item.relatedId) {
    void router.push(`/items/lost/${item.relatedId}`);
  }
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

onMounted(load);
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <span class="eyebrow">Messages</span>
        <h1>消息中心</h1>
        <p>实时跟进认领、匹配、积分与系统通知</p>
      </div>
      <el-button type="primary" plain :disabled="!noticeStore.unreadTotal" @click="handleMarkAll">
        全部标记为已读
      </el-button>
    </header>

    <el-skeleton v-if="loading" :rows="4" animated />
    <template v-else>
      <el-card v-if="list.length" shadow="never" :body-style="{ padding: 0 }">
        <div
          v-for="n in list"
          :key="n.id"
          class="row"
          :class="{ unread: !n.isRead }"
          @click="handleClick(n)"
        >
          <div class="dot" />
          <div class="body">
            <div class="meta">
              <el-tag size="small" effect="plain">{{ noticeTypeLabels[n.noticeType] }}</el-tag>
              <span class="time">{{ relativeTime(n.createdAt) }}</span>
            </div>
            <strong>{{ n.title }}</strong>
            <p>{{ n.content }}</p>
          </div>
          <el-tag v-if="n.priority === 'HIGH'" type="danger" size="small">高优</el-tag>
        </div>
      </el-card>
      <EmptyState v-else title="暂无消息">
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
        @current-change="load"
      />
    </template>
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

.row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--xunji-border);
  cursor: pointer;
  transition: background 0.18s;

  &:hover {
    background: rgba(13, 79, 79, 0.04);
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
    flex: 1;
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
    p {
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
</style>
