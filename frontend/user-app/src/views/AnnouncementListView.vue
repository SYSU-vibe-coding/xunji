<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { Bell } from '@element-plus/icons-vue';

import EmptyState from '@/components/EmptyState.vue';
import { listAnnouncements } from '@/api/notification';
import { ApiError, isAuthApiError } from '@/api/http';
import type { AnnouncementSummary } from '@xunji/shared';

const router = useRouter();
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
    errorMessage.value = err instanceof ApiError ? err.message : '公告加载失败';
  } finally {
    loading.value = false;
  }
}

function open(id: string) {
  void router.push(`/announcements/${id}`);
}

onMounted(load);
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <span class="eyebrow">Campus Bulletin</span>
        <h1>校园公告</h1>
        <p>查看平台维护、失物集中处理和校园服务动态</p>
      </div>
    </header>

    <el-skeleton v-if="loading" :rows="5" animated />
    <EmptyState
      v-else-if="errorMessage"
      title="公告加载失败"
      :description="errorMessage"
      action-text="重试"
      @action="load"
    />
    <div v-else-if="list.length" class="announcement-list">
      <article v-for="item in list" :key="item.id" class="announcement" @click="open(item.id)">
        <div class="date-block">
          <span>{{ item.publishedAt.slice(5, 10) }}</span>
          <small>{{ item.publishedAt.slice(0, 4) }}</small>
        </div>
        <div class="announcement-title">
          <span class="published">已发布</span>
          <h2>{{ item.title }}</h2>
          <p>{{ item.publishedAt }}</p>
        </div>
        <span class="open-link">查看详情</span>
      </article>
    </div>
    <EmptyState v-else title="暂无公告" description="已发布公告会显示在这里">
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
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.page-header {
  padding: 20px 22px;
  color: #fff;
  border-radius: 16px;
  background:
    linear-gradient(110deg, rgba(13, 79, 79, 0.96), rgba(20, 184, 166, 0.78)),
    radial-gradient(circle at 80% 10%, #fff 0 2px, transparent 3px);
  .eyebrow {
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    opacity: 0.72;
  }
  h1 {
    margin: 7px 0 5px;
    font-size: 24px;
  }
  p {
    margin: 0;
    font-size: 13px;
    opacity: 0.8;
  }
}
.announcement-list {
  overflow: hidden;
  border: 1px solid var(--xunji-border);
  border-radius: 14px;
  background: var(--xunji-surface);
}
.announcement {
  display: grid;
  grid-template-columns: 76px 1fr auto;
  align-items: center;
  gap: 18px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--xunji-border);
  cursor: pointer;
  transition: background 0.16s, transform 0.16s;
  &:last-child {
    border-bottom: none;
  }
  &:hover {
    background: rgba(13, 79, 79, 0.04);
    .open-link {
      transform: translateX(3px);
    }
  }
}
.date-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 9px 6px;
  color: var(--el-color-primary);
  border-radius: 10px;
  background: rgba(13, 79, 79, 0.07);
  font-variant-numeric: tabular-nums;
  span {
    font-size: 17px;
    font-weight: 700;
  }
  small {
    font-size: 11px;
  }
}
.announcement-title {
  min-width: 0;
  .published {
    color: var(--el-color-primary);
    font-size: 11px;
  }
  h2 {
    margin: 4px 0;
    overflow: hidden;
    font-size: 16px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  p {
    margin: 0;
    color: var(--xunji-text-muted);
    font-size: 12px;
  }
}
.open-link {
  color: var(--el-color-primary);
  font-size: 13px;
  transition: transform 0.16s;
}
.pagination {
  justify-content: center;
}
@media (max-width: 640px) {
  .announcement {
    grid-template-columns: 62px 1fr;
    gap: 12px;
    padding: 14px;
  }
  .open-link {
    display: none;
  }
}
</style>
