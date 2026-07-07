<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { Trophy } from '@element-plus/icons-vue';

import EmptyState from '@/components/EmptyState.vue';
import PageHeader from '@/components/PageHeader.vue';
import { listMyCreditLogs } from '@/api/credit';
import { isAuthApiError } from '@/api/http';
import { useAuthStore } from '@/stores/auth';
import type { CreditLogItem } from '@xunji/shared';
import { creditReasonLabels } from '@xunji/shared';
import { shortDateTime } from '@/utils/format';

const auth = useAuthStore();
const list = ref<CreditLogItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const loading = ref(true);

async function load() {
  loading.value = true;
  try {
    const data = await listMyCreditLogs({ pageNo: page.value, pageSize });
    list.value = data.list;
    total.value = data.total;
  } catch (err) {
    if (isAuthApiError(err)) return;
    list.value = [];
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Credits"
      title="信誉积分"
      description="积分变动记录全程可追溯，奖惩透明公正"
      back-fallback="/profile"
    />

    <el-card shadow="never" class="hero xunji-hero">
      <div class="row">
        <el-icon :size="32"><Trophy /></el-icon>
        <div>
          <span>当前信誉分</span>
          <strong>{{ auth.profile?.creditScore ?? '—' }}</strong>
        </div>
      </div>
    </el-card>

    <el-skeleton v-if="loading" :rows="3" animated />
    <template v-else>
      <el-table v-if="list.length" :data="list" stripe border style="width: 100%">
        <el-table-column prop="createdAt" label="时间" width="180">
          <template #default="{ row }">{{ shortDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="变动" width="100">
          <template #default="{ row }">
            <el-tag :type="row.deltaScore > 0 ? 'success' : 'danger'" effect="plain">
              {{ row.deltaScore > 0 ? '+' : '' }}{{ row.deltaScore }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="原因">
          <template #default="{ row }">
            <strong>{{ creditReasonLabels[row.reasonCode as keyof typeof creditReasonLabels] || row.reasonCode }}</strong>
            <div v-if="row.reasonText" class="muted">{{ row.reasonText }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="bizType" label="业务" width="100" />
      </el-table>
      <EmptyState v-else title="暂无积分变动" description="完成认领、交接等操作后将自动产生积分流水" />

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
.hero {
  color: #fff;
  border: none;

  :deep(.el-card__body) {
    padding: 22px 24px;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 16px;

    span {
      display: block;
      color: rgba(255, 255, 255, 0.78);
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }
    strong {
      font-size: 36px;
      font-weight: 700;
    }
  }
}
.muted {
  margin-top: 4px;
  color: var(--xunji-text-muted);
  font-size: 12px;
}
.pagination {
  justify-content: center;
}
</style>
