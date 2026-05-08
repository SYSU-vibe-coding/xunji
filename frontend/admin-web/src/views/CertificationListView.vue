<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';

import StatusTag from '@/components/StatusTag.vue';
import { listCertifications, reviewCertification } from '@/api/admin';
import { ApiError, isAuthApiError } from '@/api/http';
import {
  type CertificationReview,
  type ReviewStatus,
  reviewStatusLabels,
} from '@xunji/shared';
import { shortDateTime } from '@/utils/format';

const list = ref<CertificationReview[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 10;
const reviewStatus = ref<ReviewStatus | ''>('');
const loading = ref(true);

const previewSrc = ref<string>('');
const previewVisible = ref(false);

async function load() {
  loading.value = true;
  try {
    const data = await listCertifications({
      pageNo: page.value,
      pageSize,
      reviewStatus: (reviewStatus.value || undefined) as ReviewStatus | undefined,
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

async function approve(record: CertificationReview) {
  try {
    await reviewCertification(record.id, { action: 'APPROVE', comment: '资料清晰，审核通过' });
    ElMessage.success(`已通过 ${record.realName ?? record.campusId}`);
    await load();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  }
}

async function reject(record: CertificationReview) {
  try {
    const result = await ElMessageBox.prompt('请输入驳回原因', '驳回认证', {
      confirmButtonText: '提交驳回',
      cancelButtonText: '取消',
      inputValidator: (v) => (v && v.trim().length > 0) || '驳回原因不能为空',
    });
    await reviewCertification(record.id, { action: 'REJECT', comment: result.value });
    ElMessage.success(`已驳回 ${record.realName ?? record.campusId}`);
    await load();
  } catch (err) {
    if (err === 'cancel' || err === 'close') return;
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  }
}

function showImage(url: string) {
  previewSrc.value = url;
  previewVisible.value = true;
}

onMounted(load);
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="filter-card">
      <el-radio-group
        v-model="reviewStatus"
        @change="
          () => {
            page = 1;
            load();
          }
        "
      >
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button v-for="(label, key) in reviewStatusLabels" :key="key" :label="key">
          {{ label }}
        </el-radio-button>
      </el-radio-group>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="list" stripe border style="width: 100%">
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
        <el-table-column label="提交时间" width="180">
          <template #default="{ row }">{{ shortDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center">
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
              驳回
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
