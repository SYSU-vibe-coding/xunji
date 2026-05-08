<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Search } from '@element-plus/icons-vue';

import StatusTag from '@/components/StatusTag.vue';
import { changeUserStatus, listAdminUsers } from '@/api/admin';
import { ApiError, isAuthApiError } from '@/api/http';
import {
  type AdminUserRecord,
  type UserRole,
  type UserStatus,
  userRoleLabels,
  userStatusLabels,
} from '@xunji/shared';
import { shortDateTime } from '@/utils/format';

const route = useRoute();

const list = ref<AdminUserRecord[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 10;
const keyword = ref(typeof route.query.keyword === 'string' ? route.query.keyword : '');
const role = ref<UserRole | ''>('');
const status = ref<UserStatus | ''>('');
const loading = ref(true);

async function load() {
  loading.value = true;
  try {
    const data = await listAdminUsers({
      pageNo: page.value,
      pageSize,
      keyword: keyword.value.trim() || undefined,
      role: role.value || undefined,
      status: status.value || undefined,
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

async function toggleStatus(record: AdminUserRecord) {
  if (record.role === 'ADMIN') {
    ElMessage.warning('管理员账号不能在此处修改状态');
    return;
  }
  const next = record.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE';
  const verb = next === 'DISABLED' ? '禁用' : '启用';
  try {
    await changeUserStatus(record.id, {
      status: next,
      reason: next === 'DISABLED' ? '后台风控处理' : '后台恢复账号',
    });
    ElMessage.success(`已${verb}`);
    await load();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  }
}

function search() {
  page.value = 1;
  void load();
}

watch(
  () => route.query.keyword,
  (value) => {
    const next = typeof value === 'string' ? value : '';
    if (next === keyword.value) return;
    keyword.value = next;
    search();
  },
);

onMounted(load);
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="filter-card">
      <div class="filters">
        <el-input
          v-model="keyword"
          size="large"
          placeholder="搜索：手机号 / 昵称 / 用户 ID"
          clearable
          class="keyword"
          @keyup.enter="search"
          @clear="search"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
          <template #append>
            <el-button @click="search">搜索</el-button>
          </template>
        </el-input>
        <el-select
          v-model="role"
          clearable
          placeholder="角色"
          style="width: 150px"
          @change="search"
          @clear="search"
        >
          <el-option
            v-for="(label, value) in userRoleLabels"
            :key="value"
            :label="label"
            :value="value"
          />
        </el-select>
        <el-select
          v-model="status"
          clearable
          placeholder="账号状态"
          style="width: 150px"
          @change="search"
          @clear="search"
        >
          <el-option
            v-for="(label, value) in userStatusLabels"
            :key="value"
            :label="label"
            :value="value"
          />
        </el-select>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="list" stripe border style="width: 100%">
        <el-table-column label="用户" min-width="200">
          <template #default="{ row }">
            <strong>{{ row.nickname }}</strong>
            <div class="muted">{{ row.phone }}</div>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">
              {{ userRoleLabels[row.role as keyof typeof userRoleLabels] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="认证" width="120">
          <template #default="{ row }">
            <StatusTag variant="cert" :value="row.certStatus" />
          </template>
        </el-table-column>
        <el-table-column prop="creditScore" label="信用分" width="100" align="center" />
        <el-table-column label="账号状态" width="120">
          <template #default="{ row }">
            <StatusTag variant="user" :value="row.status" />
          </template>
        </el-table-column>
        <el-table-column label="注册时间" width="160">
          <template #default="{ row }">{{ shortDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="center" fixed="right">
          <template #default="{ row }">
            <el-popconfirm
              v-if="row.role !== 'ADMIN'"
              :title="`${row.status === 'ACTIVE' ? '禁用' : '启用'}该用户？`"
              @confirm="toggleStatus(row)"
            >
              <template #reference>
                <el-button
                  size="small"
                  :type="row.status === 'ACTIVE' ? 'danger' : 'primary'"
                  plain
                >
                  {{ row.status === 'ACTIVE' ? '禁用' : '启用' }}
                </el-button>
              </template>
            </el-popconfirm>
            <span v-else class="muted">管理员</span>
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
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.keyword {
  max-width: 420px;
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
