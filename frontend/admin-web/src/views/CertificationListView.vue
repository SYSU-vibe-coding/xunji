<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';

import StatusTag from '@/components/StatusTag.vue';
import { listCertifications, reviewCertification } from '@/api/admin';
import { ApiError, isUnauthorizedApiError } from '@/api/http';
import {
  type CertificationReview,
  type ReviewStatus,
  isConflictApiError,
  reviewStatusLabels,
} from '@xunji/shared';
import { shortDateTime } from '@/utils/format';
import { createLatestRequestGuard, lastPage, queryEnum, queryPositiveInt } from '@/utils/admin-list';

const route = useRoute();
const router = useRouter();
const requestGuard = createLatestRequestGuard();

const list = ref<CertificationReview[]>([]);
const total = ref(0);
const pageSize = 10;
const page = ref(queryPositiveInt(route.query.page));
const reviewStatus = ref<ReviewStatus | ''>(
  queryEnum(route.query.reviewStatus, Object.keys(reviewStatusLabels) as ReviewStatus[]),
);
const loading = ref(true);
const errorMessage = ref('');
const actionLoadingId = ref('');

const previewSrc = ref<string>('');
const previewVisible = ref(false);

function currentQuery() {
  return {
    ...(reviewStatus.value ? { reviewStatus: reviewStatus.value } : {}),
    ...(page.value > 1 ? { page: String(page.value) } : {}),
  };
}

async function syncUrl() {
  await router.replace({ query: currentQuery() });
}

async function load() {
  const requestId = requestGuard.next();
  loading.value = true;
  errorMessage.value = '';
  try {
    const data = await listCertifications({
      pageNo: page.value,
      pageSize,
      reviewStatus: (reviewStatus.value || undefined) as ReviewStatus | undefined,
    });
    if (!requestGuard.isLatest(requestId)) return;
    const finalPage = lastPage(data.total, pageSize);
    if (page.value > finalPage) {
      page.value = finalPage;
      await syncUrl();
      if (requestGuard.isLatest(requestId)) void load();
      return;
    }
    list.value = data.list;
    total.value = data.total;
  } catch (err) {
    if (!requestGuard.isLatest(requestId) || isUnauthorizedApiError(err)) return;
    list.value = [];
    total.value = 0;
    errorMessage.value = err instanceof ApiError ? err.message : '认证列表加载失败';
  } finally {
    if (requestGuard.isLatest(requestId)) loading.value = false;
  }
}

async function approve(record: CertificationReview) {
  if (actionLoadingId.value) return;
  actionLoadingId.value = record.id;
  try {
    await ElMessageBox.confirm(
      `确认通过 ${record.realName ?? record.campusId} 的校园认证？通过后将授予认证状态并增加 20 信用分。`,
      '确认通过认证',
      { type: 'warning', confirmButtonText: '确认通过', cancelButtonText: '取消' },
    );
    await reviewCertification(record.id, { action: 'APPROVE', comment: '资料清晰，审核通过' });
    ElMessage.success(`已通过 ${record.realName ?? record.campusId}`);
    await load();
  } catch (err) {
    if (err === 'cancel' || err === 'close') return;
    if (isConflictApiError(err)) {
      ElMessage.warning('认证审核状态已变化，已刷新最新列表');
      await load();
      return;
    }
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  } finally {
    actionLoadingId.value = '';
  }
}

async function reject(record: CertificationReview) {
  if (actionLoadingId.value) return;
  actionLoadingId.value = record.id;
  try {
    const result = await ElMessageBox.prompt('请输入驳回原因。确认后认证将被驳回。', '确认驳回认证', {
      confirmButtonText: '提交驳回',
      cancelButtonText: '取消',
      inputValidator: (v) => (v && v.trim().length > 0) || '驳回原因不能为空',
    });
    await reviewCertification(record.id, { action: 'REJECT', comment: result.value.trim() });
    ElMessage.success(`已驳回 ${record.realName ?? record.campusId}`);
    await load();
  } catch (err) {
    if (err === 'cancel' || err === 'close') return;
    if (isConflictApiError(err)) {
      ElMessage.warning('认证审核状态已变化，已刷新最新列表');
      await load();
      return;
    }
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  } finally {
    actionLoadingId.value = '';
  }
}

function showImage(url: string) {
  previewSrc.value = url;
  previewVisible.value = true;
}

async function refresh() {
  await syncUrl();
  await load();
}

function filter() {
  page.value = 1;
  void refresh();
}

watch(
  () => route.query,
  (query) => {
    const nextStatus = queryEnum(
      query.reviewStatus,
      Object.keys(reviewStatusLabels) as ReviewStatus[],
    );
    const nextPage = queryPositiveInt(query.page);
    if (nextStatus === reviewStatus.value && nextPage === page.value) return;
    reviewStatus.value = nextStatus;
    page.value = nextPage;
    void load();
  },
);

onMounted(load);
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="filter-card">
      <el-radio-group
        v-model="reviewStatus"
        @change="filter"
      >
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button v-for="(label, key) in reviewStatusLabels" :key="key" :label="key">
          {{ label }}
        </el-radio-button>
      </el-radio-group>
    </el-card>

    <el-card shadow="never">
      <el-result v-if="errorMessage" icon="error" title="认证列表加载失败" :sub-title="errorMessage">
        <template #extra><el-button type="primary" @click="load">重试</el-button></template>
      </el-result>
      <el-table v-else-if="loading || list.length" v-loading="loading" :data="list" stripe border style="width: 100%">
        <el-table-column label="申请人" min-width="160">
          <template #default="{ row }">
            <strong>{{ row.realName || '—' }}</strong>
            <div class="muted">{{ row.nickname }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="campusId" label="校园编号" width="160" />
        <el-table-column label="证件" width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click="showImage(row.documentImageUrl)">
              查看图片
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <StatusTag variant="review" :value="row.reviewStatus" />
          </template>
        </el-table-column>
        <el-table-column prop="reviewComment" label="审核意见" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.reviewComment || '—' }}</template>
        </el-table-column>
        <el-table-column label="提交时间" width="180">
          <template #default="{ row }">{{ shortDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              :disabled="row.reviewStatus !== 'PENDING' || Boolean(actionLoadingId)"
              :loading="actionLoadingId === row.id"
              @click="approve(row)"
            >
              通过
            </el-button>
            <el-button
              type="danger"
              plain
              size="small"
              :disabled="row.reviewStatus !== 'PENDING' || Boolean(actionLoadingId)"
              :loading="actionLoadingId === row.id"
              @click="reject(row)"
            >
              驳回
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="当前筛选条件下没有认证申请" />

      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        background
        class="pagination"
        @current-change="refresh"
      />
    </el-card>

    <el-dialog v-model="previewVisible" title="证件图片" width="520px">
      <el-image
        v-if="previewSrc"
        :src="previewSrc"
        fit="contain"
        style="width: 100%; max-height: 500px"
      />
    </el-dialog>
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
