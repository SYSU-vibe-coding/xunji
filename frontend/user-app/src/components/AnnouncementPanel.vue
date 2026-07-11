<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { ArrowRight, Reading } from '@element-plus/icons-vue';

import EmptyState from '@/components/EmptyState.vue';
import { ApiError, isAuthApiError } from '@/api/http';
import { listAnnouncements } from '@/api/notification';
import type { AnnouncementSummary } from '@xunji/shared';

const list = ref<AnnouncementSummary[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 10;
const loading = ref(true);
const errorMessage = ref('');

async function load() {
  loading.value = true;
  errorMessage.value = '';
  try {
    const data = await listAnnouncements({ pageNo: page.value, pageSize });
    list.value = data.list;
    total.value = data.total;
  } catch (err) {
    if (isAuthApiError(err)) return;
    list.value = [];
    total.value = 0;
    errorMessage.value = err instanceof ApiError ? err.message : '公告加载失败，请稍后重试';
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="announcement-panel" aria-label="公告列表" aria-live="polite">
    <el-skeleton v-if="loading" :rows="5" animated />
    <EmptyState
      v-else-if="errorMessage"
      title="公告加载失败"
      :description="errorMessage"
      action-text="重试"
      @action="load"
    />
    <ul v-else-if="list.length" class="announcement-list">
      <li v-for="item in list" :key="item.id">
        <RouterLink
          :to="`/announcements/${item.id}`"
          class="announcement"
          :aria-label="`查看公告：${item.title}`"
        >
          <time class="date-block" :datetime="item.publishedAt">
            <span>{{ item.publishedAt.slice(5, 10) }}</span>
            <small>{{ item.publishedAt.slice(0, 4) }}</small>
          </time>
          <span class="announcement-title">
            <span class="published">校园公告</span>
            <strong>{{ item.title }}</strong>
            <time :datetime="item.publishedAt">{{ item.publishedAt }}</time>
          </span>
          <span class="open-link" aria-hidden="true">
            查看详情 <el-icon><ArrowRight /></el-icon>
          </span>
        </RouterLink>
      </li>
    </ul>
    <EmptyState v-else title="暂无公告" description="已发布公告会显示在这里">
      <template #icon><Reading /></template>
    </EmptyState>

    <el-pagination
      v-if="!loading && !errorMessage && total > pageSize"
      v-model:current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next"
      background
      class="pagination"
      aria-label="公告分页"
      @current-change="load"
    />
  </section>
</template>

<style scoped lang="scss">
.announcement-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.announcement-list {
  margin: 0;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--xunji-border);
  border-radius: 14px;
  background: var(--xunji-surface);
  list-style: none;

  li:not(:last-child) {
    border-bottom: 1px solid var(--xunji-border);
  }
}

.announcement {
  display: grid;
  grid-template-columns: 70px minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  padding: 16px 18px;
  color: inherit;
  text-decoration: none;
  transition: background 0.16s;

  &:hover,
  &:focus-visible {
    background: rgba(13, 79, 79, 0.045);
    .open-link {
      transform: translateX(2px);
    }
  }
  &:focus-visible {
    outline: 2px solid var(--el-color-primary);
    outline-offset: -2px;
  }
}

.date-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 5px;
  color: var(--el-color-primary);
  border-radius: 10px;
  background: rgba(13, 79, 79, 0.07);
  font-variant-numeric: tabular-nums;
  span {
    font-size: 16px;
    font-weight: 700;
  }
  small {
    font-size: 11px;
  }
}

.announcement-title {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  .published {
    color: var(--el-color-primary);
    font-size: 11px;
  }
  strong {
    max-width: 100%;
    overflow: hidden;
    color: var(--xunji-text);
    font-size: 15px;
    font-weight: 650;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  time {
    color: var(--xunji-text-muted);
    font-size: 12px;
  }
}

.open-link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--el-color-primary);
  font-size: 12px;
  transition: transform 0.16s;
}

.pagination {
  justify-content: center;
}

@media (max-width: 640px) {
  .announcement {
    grid-template-columns: 58px minmax(0, 1fr);
    gap: 11px;
    padding: 14px 12px;
  }
  .open-link {
    display: none;
  }
  .announcement-title time {
    overflow: hidden;
    max-width: 100%;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
