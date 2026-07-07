<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';

import StatusTag from '@/components/StatusTag.vue';
import { listItemReviews, reviewItem } from '@/api/admin';
import { ApiError, isAuthApiError } from '@/api/http';
import {
  type ItemReviewRecord,
  categoryLabels,
} from '@xunji/shared';
import { shortDateTime } from '@/utils/format';

const route = useRoute();

function normalizeBizType(value: unknown): 'LOST' | 'FOUND' | '' {
  if (value === 'lost' || value === 'LOST') return 'LOST';
  if (value === 'found' || value === 'FOUND') return 'FOUND';
  return '';
}

const list = ref<ItemReviewRecord[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 10;
const bizType = ref<'LOST' | 'FOUND' | ''>(normalizeBizType(route.query.bizType));
const loading = ref(true);

async function load() {
  loading.value = true;
  try {
    const data = await listItemReviews({
      pageNo: page.value,
      pageSize,
      bizType: (bizType.value || undefined) as 'LOST' | 'FOUND' | undefined,
    });
    list.value = data.list;
    total.value = data.total;
  } catch (err) {
    if (isAuthApiError(err)) return;
    list.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

async function approve(record: ItemReviewRecord) {
  try {
    await reviewItem(record.bizType, record.id, { action: 'APPROVE' });
    ElMessage.success(`已通过 ${record.itemName}`);
    await load();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  }
}

async function reject(record: ItemReviewRecord) {
  try {
    const result = await ElMessageBox.prompt('请输入关闭原因', '关闭物品', {
      confirmButtonText: '确认关闭',
      cancelButtonText: '取消',
      inputValidator: (v) => (v && v.trim().length > 0) || '关闭原因不能为空',
    });
    await reviewItem(record.bizType, record.id, { action: 'REJECT', comment: result.value });
    ElMessage.success(`已关闭 ${record.itemName}`);
    await load();
  } catch (err) {
    if (err === 'cancel' || err === 'close') return;
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  }
}

watch(bizType, () => {
  page.value = 1;
  void load();
});

watch(
  () => route.query.bizType,
  (value) => {
    const next = normalizeBizType(value);
    if (next === bizType.value) return;
    bizType.value = next;
  },
);

onMounted(load);
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="filter-card">
      <el-radio-group v-model="bizType">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="FOUND">招领</el-radio-button>
        <el-radio-button label="LOST">失物</el-radio-button>
      </el-radio-group>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="list" stripe border style="width: 100%">
        <el-table-column label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.bizType === 'FOUND' ? 'success' : 'warning'" effect="plain" size="small">
              {{ row.bizType === 'FOUND' ? '招领' : '失物' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="物品" min-width="180">
          <template #default="{ row }">
            <strong>{{ row.itemName }}</strong>
            <div class="muted">{{ row.ownerNickname || '—' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类别" width="100">
          <template #default="{ row }">{{ categoryLabels[row.category as keyof typeof categoryLabels] }}</template>
        </el-table-column>
        <el-table-column prop="location" label="地点" min-width="160" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :variant="row.bizType === 'FOUND' ? 'found' : 'lost'" :value="row.status" />
          </template>
        </el-table-column>
        <el-table-column label="审核" width="100">
          <template #default="{ row }">
            <StatusTag variant="review" :value="row.reviewStatus" />
          </template>
        </el-table-column>
        <el-table-column prop="reportCount" label="举报数" width="100" align="center" />
        <el-table-column label="敏感" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.isSensitive" type="danger" effect="plain" size="small">敏感</el-tag>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="160">
          <template #default="{ row }">{{ shortDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              :disabled="row.reviewStatus !== 'PENDING'"
              @click="approve(row)"
            >
              通过
            </el-button>
            <el-button
              type="danger"
              plain
              size="small"
              :disabled="row.reviewStatus !== 'PENDING'"
              @click="reject(row)"
            >
              关闭
            </el-button>
          </template>
        </el-table-column>
      </el-table>

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
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.filter-card :deep(.el-card__body) {
  padding: 14px 16px;
}
.muted {
  color: var(--xunji-text-muted);
  font-size: 12px;
}
.pagination {
  margin-top: 14px;
  justify-content: center;
}
</style>
