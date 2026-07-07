<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { Document } from '@element-plus/icons-vue';

import { listOperationLogs } from '@/api/admin';
import { isAuthApiError } from '@/api/http';
import StatusTag from '@/components/StatusTag.vue';
import type { OperationLogRecord } from '@xunji/shared';
import { shortDateTime } from '@/utils/format';

const BIZ_TYPES = ['LOST', 'FOUND', 'CLAIM', 'CREDIT', 'CERTIFICATION', 'REPORT', 'ANNOUNCEMENT', 'USER', 'MATCH'];
const ACTIONS = [
  'CREATE',
  'UPDATE',
  'UPDATE_STATUS',
  'DELETE',
  'APPROVE',
  'REJECT',
  'HANDOVER',
  'CONFIRM',
  'PUBLISH',
  'VALID',
  'INVALID',
  'RUN',
  'SUBMIT',
  'REVIEW',
];
const ROLES = ['USER', 'ADMIN'];

const list = ref<OperationLogRecord[]>([]);
const total = ref(0);
const loading = ref(false);
const pageNo = ref(1);
const pageSize = ref(20);
const filters = ref({
  bizType: '' as string,
  action: '' as string,
  operatorRole: '' as string,
  keyword: '' as string,
});

async function load() {
  loading.value = true;
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
    list.value = data.list;
    total.value = data.total;
  } catch (err) {
    if (!isAuthApiError(err)) ElMessage.error('加载操作日志失败');
  } finally {
    loading.value = false;
  }
}

function applyFilters() {
  pageNo.value = 1;
  load();
}

function resetFilters() {
  filters.value = { bizType: '', action: '', operatorRole: '', keyword: '' };
  pageNo.value = 1;
  load();
}

function onPageChange(p: number) {
  pageNo.value = p;
  load();
}

function onSizeChange(s: number) {
  pageSize.value = s;
  pageNo.value = 1;
  load();
}

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
          <el-button @click="load">刷新</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="list" stripe style="width: 100%">
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

      <div class="pager">
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
