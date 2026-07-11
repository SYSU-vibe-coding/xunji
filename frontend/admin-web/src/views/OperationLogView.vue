<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Document } from '@element-plus/icons-vue';

import { listOperationLogs } from '@/api/admin';
import { ApiError, isUnauthorizedApiError } from '@/api/http';
import StatusTag from '@/components/StatusTag.vue';
import type { OperationLogRecord } from '@xunji/shared';
import { shortDateTime } from '@/utils/format';
import {
  createLatestRequestGuard,
  lastPage,
  queryEnum,
  queryPositiveInt,
  queryValue,
} from '@/utils/admin-list';

const BIZ_TYPES = ['LOST', 'FOUND', 'CLAIM', 'CERT', 'REPORT', 'ANNOUNCEMENT', 'USER', 'MATCH'] as const;
const ACTIONS = [
  'CREATE',
  'UPDATE',
  'UPDATE_STATUS',
  'DELETE',
  'REVIEW_APPROVE',
  'REVIEW_REJECT',
  'HANDOVER_CONFIRM',
  'CREDIT_CHANGE',
  'REPORT_HANDLE',
  'CERT_APPROVE',
  'CERT_REJECT',
  'RUN',
] as const;
const ROLES = ['USER', 'ADMIN'] as const;

const route = useRoute();
const router = useRouter();
const requestGuard = createLatestRequestGuard();

const list = ref<OperationLogRecord[]>([]);
const total = ref(0);
const loading = ref(true);
const errorMessage = ref('');
const pageNo = ref(queryPositiveInt(route.query.page));
const pageSize = ref(queryEnum(route.query.pageSize, ['20', '50', '100'] as const)
  ? Number(queryValue(route.query.pageSize))
  : 20);
const filters = ref({
  bizType: queryEnum(route.query.bizType, BIZ_TYPES) as string,
  action: queryEnum(route.query.action, ACTIONS) as string,
  operatorRole: queryEnum(route.query.operatorRole, ROLES) as string,
  keyword: queryValue(route.query.keyword),
});

function currentQuery() {
  return {
    ...(filters.value.bizType ? { bizType: filters.value.bizType } : {}),
    ...(filters.value.action ? { action: filters.value.action } : {}),
    ...(filters.value.operatorRole ? { operatorRole: filters.value.operatorRole } : {}),
    ...(filters.value.keyword.trim() ? { keyword: filters.value.keyword.trim() } : {}),
    ...(pageNo.value > 1 ? { page: String(pageNo.value) } : {}),
    ...(pageSize.value !== 20 ? { pageSize: String(pageSize.value) } : {}),
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
    const params: Record<string, unknown> = {
      pageNo: pageNo.value,
      pageSize: pageSize.value,
    };
    if (filters.value.bizType) params.bizType = filters.value.bizType;
    if (filters.value.action) params.action = filters.value.action;
    if (filters.value.operatorRole) params.operatorRole = filters.value.operatorRole;
    if (filters.value.keyword) params.keyword = filters.value.keyword;
    const data = await listOperationLogs(params);
    if (!requestGuard.isLatest(requestId)) return;
    const finalPage = lastPage(data.total, pageSize.value);
    if (pageNo.value > finalPage) {
      pageNo.value = finalPage;
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
    errorMessage.value = err instanceof ApiError ? err.message : '操作日志加载失败';
  } finally {
    if (requestGuard.isLatest(requestId)) loading.value = false;
  }
}

async function refresh() {
  await syncUrl();
  await load();
}

function applyFilters() {
  pageNo.value = 1;
  void refresh();
}

function resetFilters() {
  filters.value = { bizType: '', action: '', operatorRole: '', keyword: '' };
  pageNo.value = 1;
  void refresh();
}

function onPageChange(p: number) {
  pageNo.value = p;
  void refresh();
}

function onSizeChange(s: number) {
  pageSize.value = s;
  pageNo.value = 1;
  void refresh();
}

watch(
  () => route.query,
  (query) => {
    const nextPage = queryPositiveInt(query.page);
    const nextPageSizeValue = queryEnum(query.pageSize, ['20', '50', '100'] as const);
    const nextPageSize = nextPageSizeValue ? Number(nextPageSizeValue) : 20;
    const nextFilters = {
      bizType: queryEnum(query.bizType, BIZ_TYPES) as string,
      action: queryEnum(query.action, ACTIONS) as string,
      operatorRole: queryEnum(query.operatorRole, ROLES) as string,
      keyword: queryValue(query.keyword),
    };
    if (
      nextPage === pageNo.value &&
      nextPageSize === pageSize.value &&
      Object.entries(nextFilters).every(
        ([key, value]) => filters.value[key as keyof typeof filters.value] === value,
      )
    ) return;
    pageNo.value = nextPage;
    pageSize.value = nextPageSize;
    filters.value = nextFilters;
    void load();
  },
);

onMounted(load);
</script>

<template>
  <div class="page">
    <el-page-header :icon="Document" title="返回" @back="$router.push('/dashboard')">
      <template #content>
        <span class="page-title">操作日志</span>
      </template>
    </el-page-header>

    <el-card shadow="never">
      <template #header>
        <div class="filter-row">
          <el-select v-model="filters.bizType" placeholder="业务类型" clearable style="width: 150px">
            <el-option v-for="t in BIZ_TYPES" :key="t" :label="t" :value="t" />
          </el-select>
          <el-select v-model="filters.action" placeholder="操作动作" clearable style="width: 150px">
            <el-option v-for="a in ACTIONS" :key="a" :label="a" :value="a" />
          </el-select>
          <el-select v-model="filters.operatorRole" placeholder="操作者角色" clearable style="width: 140px">
            <el-option v-for="r in ROLES" :key="r" :label="r" :value="r" />
          </el-select>
          <el-input
            v-model="filters.keyword"
            placeholder="搜索详情"
            clearable
            style="width: 200px"
            @keyup.enter="applyFilters"
          />
          <el-button type="primary" @click="applyFilters">筛选</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button :loading="loading" @click="refresh">刷新</el-button>
        </div>
      </template>

      <el-result v-if="errorMessage" icon="error" title="操作日志加载失败" :sub-title="errorMessage">
        <template #extra><el-button type="primary" @click="load">重试</el-button></template>
      </el-result>
      <el-table v-else-if="loading || list.length" v-loading="loading" :data="list" stripe style="width: 100%">
        <el-table-column prop="createdAt" label="时间" width="160">
          <template #default="{ row }">{{ shortDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column prop="operatorRole" label="角色" width="90">
          <template #default="{ row }">
            <StatusTag variant="review" :value="row.operatorRole" />
          </template>
        </el-table-column>
        <el-table-column prop="operatorId" label="操作者ID" width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mono">{{ row.operatorId === 'SYSTEM' ? 'SYSTEM' : row.operatorId }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="bizType" label="业务" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.bizType }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="action" label="动作" width="130">
          <template #default="{ row }">
            <el-tag size="small">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" min-width="280" show-overflow-tooltip />
        <el-table-column prop="bizId" label="业务ID" width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="mono">{{ row.bizId }}</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="当前筛选条件下没有操作日志" />

      <div v-if="total > 0" class="pager">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next"
          :total="total"
          :current-page="pageNo"
          :page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          @current-change="onPageChange"
          @size-change="onSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-title {
  font-weight: 600;
  font-size: 16px;
}

.filter-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.mono {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: var(--xunji-text-muted);
}
</style>
