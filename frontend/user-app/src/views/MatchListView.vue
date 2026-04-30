<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { Aim } from '@element-plus/icons-vue';

import EmptyState from '@/components/EmptyState.vue';
import { listMatches } from '@/api/match';
import type { MatchSummary } from '@xunji/shared';

const matches = ref<MatchSummary[]>([]);
const loading = ref(true);
const isOffline = ref(false);

onMounted(async () => {
  try {
    const data = await listMatches({ pageSize: 20 });
    matches.value = data.list;
    isOffline.value = data.total === 0; // 后端未实现时 safeCall 返回空
  } catch {
    isOffline.value = true;
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="page">
    <header class="page-header">
      <span class="eyebrow">Matches</span>
      <h1>智能匹配</h1>
      <p>系统会根据你的失物自动检索相似招领</p>
    </header>

    <el-skeleton v-if="loading" :rows="3" animated />

    <template v-else>
      <div v-if="matches.length" class="grid">
        <el-card v-for="m in matches" :key="m.matchId" shadow="never" class="match-card">
          <div class="row">
            <strong>{{ m.counterpart.itemName }}</strong>
            <el-progress :percentage="Math.round(m.totalScore)" :stroke-width="6" />
          </div>
          <div class="meta">📍 {{ m.counterpart.location }} · 🕒 {{ m.counterpart.time }}</div>
        </el-card>
      </div>
      <el-card v-else shadow="never" class="empty-card">
        <EmptyState
          title="匹配引擎升级中"
          description="后端 Match 模块尚未发布，请等待团队完成对接"
        >
          <template #icon><Aim /></template>
        </EmptyState>
      </el-card>
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

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}

.match-card {
  .row {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .meta {
    margin-top: 8px;
    color: var(--xunji-text-muted);
    font-size: 12px;
  }
}
</style>
