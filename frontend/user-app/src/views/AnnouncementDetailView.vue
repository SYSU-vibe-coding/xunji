<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Document } from '@element-plus/icons-vue';

import EmptyState from '@/components/EmptyState.vue';
import { getAnnouncement } from '@/api/notification';
import { ApiError, isAuthApiError } from '@/api/http';
import type { AnnouncementDetail } from '@xunji/shared';

const route = useRoute();
const router = useRouter();
const detail = ref<AnnouncementDetail | null>(null);
const loading = ref(true);
const errorMessage = ref('');

async function load() {
  loading.value = true;
  errorMessage.value = '';
  detail.value = null;
  try {
    detail.value = await getAnnouncement(String(route.params.id));
  } catch (err) {
    if (isAuthApiError(err)) return;
    errorMessage.value = err instanceof ApiError ? err.message : '公告加载失败';
  } finally {
    loading.value = false;
  }
}

watch(() => route.params.id, load);
onMounted(load);
</script>

<template>
  <div class="page">
    <el-skeleton v-if="loading" :rows="9" animated />
    <EmptyState
      v-else-if="errorMessage"
      title="公告不可访问"
      :description="`${errorMessage}。公告可能已下线。`"
      action-text="返回公告列表"
      @action="router.push('/announcements')"
    />
    <article v-else-if="detail" class="paper">
      <div class="paper-mark"><Document /></div>
      <span class="eyebrow">Official Bulletin</span>
      <h1>{{ detail.title }}</h1>
      <div class="meta">
        <span>寻迹平台</span>
        <time>{{ detail.publishedAt }}</time>
      </div>
      <div class="rule" />
      <div class="content">{{ detail.content }}</div>
      <footer>公告编号 {{ detail.id }}</footer>
    </article>
  </div>
</template>

<style scoped lang="scss">
.page {
  max-width: 860px;
  margin: 0 auto;
}
.paper {
  position: relative;
  overflow: hidden;
  padding: clamp(28px, 6vw, 64px);
  border: 1px solid var(--xunji-border);
  border-radius: 18px;
  background: var(--xunji-surface);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.07);
  &::before {
    position: absolute;
    inset: 0 0 auto;
    height: 5px;
    background: linear-gradient(90deg, #0d4f4f, #14b8a6, #f59e0b);
    content: '';
  }
  h1 {
    max-width: 680px;
    margin: 10px 0 12px;
    font-size: clamp(26px, 5vw, 40px);
    line-height: 1.2;
    letter-spacing: -0.03em;
  }
}
.paper-mark {
  position: absolute;
  top: 34px;
  right: 42px;
  width: 64px;
  height: 64px;
  padding: 16px;
  color: rgba(13, 79, 79, 0.12);
  border: 2px solid currentColor;
  border-radius: 50%;
  transform: rotate(10deg);
}
.eyebrow {
  color: var(--el-color-primary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}
.meta {
  display: flex;
  gap: 12px;
  color: var(--xunji-text-muted);
  font-size: 13px;
}
.rule {
  width: 52px;
  height: 3px;
  margin: 28px 0;
  background: #f59e0b;
}
.content {
  min-height: 220px;
  color: var(--xunji-text);
  font-size: 16px;
  line-height: 2;
  white-space: pre-wrap;
  word-break: break-word;
}
footer {
  margin-top: 42px;
  padding-top: 16px;
  color: var(--xunji-text-muted);
  border-top: 1px dashed var(--xunji-border);
  font-size: 11px;
  font-family: monospace;
}
@media (max-width: 600px) {
  .paper-mark {
    top: 24px;
    right: 24px;
    width: 48px;
    height: 48px;
    padding: 11px;
  }
}
</style>
