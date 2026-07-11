<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';

import StatusTag from '@/components/StatusTag.vue';
import { handleReport, listReports } from '@/api/admin';
import { ApiError, isUnauthorizedApiError } from '@/api/http';
import {
  type ReportHandleStatus,
  type ReportRecord,
  type ReportTargetType,
  isConflictApiError,
  reportStatusLabels,
  reportTargetTypeLabels,
} from '@xunji/shared';
import { shortDateTime } from '@/utils/format';
import { createLatestRequestGuard, lastPage, queryEnum, queryPositiveInt } from '@/utils/admin-list';
import {
  buildReportHandlePayload,
  isSupportedReportTargetType,
  reportPenalty,
  reportTargetRoute,
} from '@/utils/report';

const route = useRoute();
const router = useRouter();
const requestGuard = createLatestRequestGuard();

const list = ref<ReportRecord[]>([]);
const total = ref(0);
const pageSize = 10;
const page = ref(queryPositiveInt(route.query.page));
const handleStatus = ref<ReportHandleStatus | ''>(
  queryEnum(route.query.handleStatus, Object.keys(reportStatusLabels) as ReportHandleStatus[]),
);
const targetType = ref<ReportTargetType | ''>(
  queryEnum(route.query.targetType, Object.keys(reportTargetTypeLabels) as ReportTargetType[]),
);
const loading = ref(true);
const errorMessage = ref('');

const dialogVisible = ref(false);
const dialogRecord = ref<ReportRecord | null>(null);
const dialogForm = reactive<{
  action: 'VALID' | 'INVALID';
  result: string;
  creditDelta: number | null;
}>({
  action: 'VALID',
  result: '',
  creditDelta: null,
});
const submitting = ref(false);

function currentQuery() {
  return {
    ...(handleStatus.value ? { handleStatus: handleStatus.value } : {}),
    ...(targetType.value ? { targetType: targetType.value } : {}),
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
    const data = await listReports({
      pageNo: page.value,
      pageSize,
      handleStatus: handleStatus.value || undefined,
      targetType: targetType.value || undefined,
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
    errorMessage.value = err instanceof ApiError ? err.message : '举报列表加载失败';
  } finally {
    if (requestGuard.isLatest(requestId)) loading.value = false;
  }
}

async function refresh() {
  await syncUrl();
  await load();
}

function search() {
  page.value = 1;
  void refresh();
}

function goTarget(record: ReportRecord) {
  const target = reportTargetRoute(record);
  if (target) void router.push(target);
}

function resetDialogForm(action: 'VALID' | 'INVALID') {
  if (!dialogRecord.value || action === 'INVALID') {
    dialogForm.result = '';
    dialogForm.creditDelta = null;
    return;
  }
  const penalty = reportPenalty(dialogRecord.value.targetType);
  dialogForm.result = penalty?.result ?? '举报有效，已记录处理结论';
  dialogForm.creditDelta = penalty?.creditDelta ?? null;
}

function openDialog(record: ReportRecord) {
  if (!isSupportedReportTargetType(record.targetType)) {
    ElMessage.warning('该举报目标类型未接入完整处置流程，前端已禁止提交');
    return;
  }
  dialogRecord.value = record;
  dialogForm.action = 'VALID';
  resetDialogForm('VALID');
  dialogVisible.value = true;
}

async function submit() {
  if (!dialogRecord.value || submitting.value) return;
  if (!dialogForm.result.trim()) {
    ElMessage.warning('请输入处理结果');
    return;
  }
  submitting.value = true;
  try {
    const payload = buildReportHandlePayload(
      dialogRecord.value,
      dialogForm.action,
      dialogForm.result,
    );
    const consequence = payload.creditDelta
      ? `并对被举报人扣减 ${Math.abs(payload.creditDelta)} 信用分`
      : '且不会自动变更信用分';
    await ElMessageBox.confirm(
      `确认将该举报判定为${dialogForm.action === 'VALID' ? '有效' : '无效'}，${consequence}？此操作不可撤销。`,
      '确认处理举报',
      { type: 'warning', confirmButtonText: '确认处理', cancelButtonText: '取消' },
    );
    await handleReport(dialogRecord.value.id, payload);
    ElMessage.success('已处理');
    dialogVisible.value = false;
    await load();
  } catch (err) {
    if (err === 'cancel' || err === 'close') return;
    if (isConflictApiError(err)) {
      dialogVisible.value = false;
      ElMessage.warning('举报处理状态已变化，已关闭旧操作并刷新列表');
      await load();
      return;
    }
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  } finally {
    submitting.value = false;
  }
}

watch(
  () => dialogForm.action,
  (action) => resetDialogForm(action),
);

watch(
  () => route.query,
  (query) => {
    const nextPage = queryPositiveInt(query.page);
    const nextStatus = queryEnum(
      query.handleStatus,
      Object.keys(reportStatusLabels) as ReportHandleStatus[],
    );
    const nextType = queryEnum(
      query.targetType,
      Object.keys(reportTargetTypeLabels) as ReportTargetType[],
    );
    if (
      nextPage === page.value &&
      nextStatus === handleStatus.value &&
      nextType === targetType.value
    ) return;
    page.value = nextPage;
    handleStatus.value = nextStatus;
    targetType.value = nextType;
    void load();
  },
);

onMounted(load);
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="filter-card">
      <div class="filters">
        <el-select
          v-model="handleStatus"
          clearable
          placeholder="处理状态"
          style="width: 160px"
          @change="search"
          @clear="search"
        >
          <el-option
            v-for="(label, value) in reportStatusLabels"
            :key="value"
            :label="label"
            :value="value"
          />
        </el-select>
        <el-select
          v-model="targetType"
          clearable
          placeholder="目标类型"
          style="width: 180px"
          @change="search"
          @clear="search"
        >
          <el-option
            v-for="(label, value) in reportTargetTypeLabels"
            :key="value"
            :label="label"
            :value="value"
          />
        </el-select>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-result v-if="errorMessage" icon="error" title="举报列表加载失败" :sub-title="errorMessage">
        <template #extra><el-button type="primary" @click="load">重试</el-button></template>
      </el-result>
      <el-table v-else-if="loading || list.length" v-loading="loading" :data="list" stripe border style="width: 100%">
        <el-table-column prop="reason" label="举报原因" min-width="180" />
        <el-table-column label="目标类型" width="120">
          <template #default="{ row }">
            {{ reportTargetTypeLabels[row.targetType as keyof typeof reportTargetTypeLabels] || '不支持的旧类型' }}
          </template>
        </el-table-column>
        <el-table-column label="目标" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link
              v-if="reportTargetRoute(row)"
              type="primary"
              :underline="false"
              @click="goTarget(row)"
            >
              {{ row.targetId }}
            </el-link>
            <span v-else>{{ row.targetId }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
        <el-table-column prop="handleResult" label="处理结果" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.handleResult || '—' }}</template>
        </el-table-column>
        <el-table-column prop="handlerId" label="处理人 ID" min-width="180">
          <template #default="{ row }">{{ row.handlerId || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <StatusTag variant="report" :value="row.handleStatus" />
          </template>
        </el-table-column>
        <el-table-column label="举报时间" width="160">
          <template #default="{ row }">{{ shortDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              :disabled="!isSupportedReportTargetType(row.targetType) || (row.handleStatus !== 'PENDING' && row.handleStatus !== 'PROCESSING')"
              :loading="submitting && dialogRecord?.id === row.id"
              @click="openDialog(row)"
            >
              处理
            </el-button>
            <div v-if="!isSupportedReportTargetType(row.targetType)" class="muted">需后端补齐处置契约</div>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="当前筛选条件下没有举报" />

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

    <el-dialog
      v-model="dialogVisible"
      title="处理举报"
      width="520px"
      :close-on-click-modal="!submitting"
      :close-on-press-escape="!submitting"
      :show-close="!submitting"
    >
      <el-form label-position="top">
        <el-form-item label="举报原因">
          <el-input :model-value="dialogRecord?.reason" disabled />
        </el-form-item>
        <el-form-item label="处理结论">
          <el-radio-group v-model="dialogForm.action">
            <el-radio-button label="VALID">举报有效</el-radio-button>
            <el-radio-button label="INVALID">举报无效</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="处理说明">
          <el-input
            v-model="dialogForm.result"
            type="textarea"
            :rows="3"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
        <el-form-item v-if="dialogForm.action === 'VALID'" label="信用分变动（被举报人）">
          <el-input-number v-model="dialogForm.creditDelta" disabled />
          <span v-if="dialogForm.creditDelta === null" class="muted">当前目标类型没有自动扣分规则</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="submitting" @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" :disabled="submitting" @click="submit">确认处理</el-button>
      </template>
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
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.muted {
  margin-left: 8px;
  color: var(--xunji-text-muted);
  font-size: 12px;
}
.pagination {
  margin-top: 14px;
  justify-content: center;
}
</style>
