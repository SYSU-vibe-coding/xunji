<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Search } from '@element-plus/icons-vue';

import StatusTag from '@/components/StatusTag.vue';
import { changeUserStatus, listAdminUsers } from '@/api/admin';
import { ApiError, isUnauthorizedApiError } from '@/api/http';
import {
  type AdminUserRecord,
  type UserRole,
  type UserStatus,
  isConflictApiError,
  userRoleLabels,
  userStatusLabels,
} from '@xunji/shared';
import { shortDateTime } from '@/utils/format';
import {
  createLatestRequestGuard,
  lastPage,
  queryEnum,
  queryPositiveInt,
  queryValue,
} from '@/utils/admin-list';

const route = useRoute();
const router = useRouter();
const requestGuard = createLatestRequestGuard();

const list = ref<AdminUserRecord[]>([]);
const total = ref(0);
const pageSize = 10;
const page = ref(queryPositiveInt(route.query.page));
const keyword = ref(queryValue(route.query.keyword));
const targetId = ref(queryValue(route.query.targetId));
const role = ref<UserRole | ''>(
  queryEnum(route.query.role, Object.keys(userRoleLabels) as UserRole[]),
);
const status = ref<UserStatus | ''>(
  queryEnum(route.query.status, Object.keys(userStatusLabels) as UserStatus[]),
);
const loading = ref(true);
const errorMessage = ref('');
const actionLoadingId = ref('');

function currentQuery() {
  return {
    ...(targetId.value ? { targetId: targetId.value } : {}),
    ...(!targetId.value && keyword.value.trim() ? { keyword: keyword.value.trim() } : {}),
    ...(!targetId.value && role.value ? { role: role.value } : {}),
    ...(!targetId.value && status.value ? { status: status.value } : {}),
    ...(!targetId.value && page.value > 1 ? { page: String(page.value) } : {}),
  };
}

async function syncUrl() {
  await router.replace({ query: currentQuery() });
}

async function findTarget(id: string) {
  let targetPage = 1;
  do {
    const data = await listAdminUsers({ pageNo: targetPage, pageSize: 50 });
    const record = data.list.find((user) => user.id === id);
    if (record) return record;
    if (targetPage >= data.totalPages) return null;
    targetPage += 1;
  } while (true);
}

async function load() {
  const requestId = requestGuard.next();
  loading.value = true;
  errorMessage.value = '';
  try {
    if (targetId.value) {
      const record = await findTarget(targetId.value);
      if (!requestGuard.isLatest(requestId)) return;
      list.value = record ? [record] : [];
      total.value = record ? 1 : 0;
      return;
    }
    const data = await listAdminUsers({
      pageNo: page.value,
      pageSize,
      keyword: keyword.value.trim() || undefined,
      role: role.value || undefined,
      status: status.value || undefined,
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
    errorMessage.value = err instanceof ApiError ? err.message : '用户列表加载失败';
  } finally {
    if (requestGuard.isLatest(requestId)) loading.value = false;
  }
}

async function toggleStatus(record: AdminUserRecord) {
  if (actionLoadingId.value) return;
  if (record.role === 'ADMIN') {
    ElMessage.warning('管理员账号不能在此处修改状态');
    return;
  }
  if (record.status === 'CANCELLED') {
    ElMessage.warning('已注销账号不可重新启用');
    return;
  }
  const next = record.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE';
  const verb = next === 'DISABLED' ? '禁用' : '启用';
  actionLoadingId.value = record.id;
  try {
    let reason: string;
    if (next === 'DISABLED') {
      const result = await ElMessageBox.prompt(
        `请输入禁用“${record.nickname}”的原因。该原因会提交后端并进入操作记录。`,
        '确认禁用用户',
        {
          type: 'warning',
          confirmButtonText: '确认禁用',
          cancelButtonText: '取消',
          inputType: 'textarea',
          inputValidator: (value) => (value && value.trim().length > 0) || '禁用原因不能为空',
          inputErrorMessage: '禁用原因不能为空',
        },
      );
      reason = result.value.trim();
    } else {
      await ElMessageBox.confirm(`确认启用“${record.nickname}”？`, '确认启用用户', {
        confirmButtonText: '确认启用',
        cancelButtonText: '取消',
      });
      reason = '后台恢复账号';
    }
    await changeUserStatus(record.id, {
      status: next,
      reason,
    });
    ElMessage.success(`已${verb}`);
    await load();
  } catch (err) {
    if (err === 'cancel' || err === 'close') return;
    if (isConflictApiError(err)) {
      ElMessage.warning('用户状态已变化，已刷新最新列表');
      await load();
      return;
    }
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  } finally {
    actionLoadingId.value = '';
  }
}

async function refresh() {
  await syncUrl();
  await load();
}

function search() {
  targetId.value = '';
  page.value = 1;
  void refresh();
}

function clearTarget() {
  targetId.value = '';
  page.value = 1;
  void refresh();
}

watch(
  () => route.query,
  (query) => {
    const nextKeyword = queryValue(query.keyword);
    const nextTargetId = queryValue(query.targetId);
    const nextRole = queryEnum(query.role, Object.keys(userRoleLabels) as UserRole[]);
    const nextStatus = queryEnum(query.status, Object.keys(userStatusLabels) as UserStatus[]);
    const nextPage = queryPositiveInt(query.page);
    if (
      nextKeyword === keyword.value &&
      nextTargetId === targetId.value &&
      nextRole === role.value &&
      nextStatus === status.value &&
      nextPage === page.value
    ) return;
    keyword.value = nextKeyword;
    targetId.value = nextTargetId;
    role.value = nextRole;
    status.value = nextStatus;
    page.value = nextPage;
    void load();
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
          placeholder="搜索：手机号 / 昵称 / 校园编号"
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
      <el-alert
        v-if="targetId"
        class="target-alert"
        type="info"
        :closable="false"
        :title="`正在按用户 ID 精确定位 ${targetId}`"
      >
        <template #default><el-button link type="primary" @click="clearTarget">清除定位</el-button></template>
      </el-alert>
    </el-card>

    <el-card shadow="never">
      <el-result v-if="errorMessage" icon="error" title="用户列表加载失败" :sub-title="errorMessage">
        <template #extra><el-button type="primary" @click="load">重试</el-button></template>
      </el-result>
      <el-table v-else-if="loading || list.length" v-loading="loading" :data="list" stripe border style="width: 100%">
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
            <el-button
              v-if="row.role !== 'ADMIN' && row.status !== 'CANCELLED'"
              size="small"
              :type="row.status === 'ACTIVE' ? 'danger' : 'primary'"
              plain
              :loading="actionLoadingId === row.id"
              :disabled="Boolean(actionLoadingId)"
              @click="toggleStatus(row)"
            >
              {{ row.status === 'ACTIVE' ? '禁用' : '启用' }}
            </el-button>
            <span v-else-if="row.role === 'ADMIN'" class="muted">管理员</span>
            <span v-else class="muted">已注销，不可启用</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty
        v-else
        :description="targetId ? `未找到用户 ${targetId}` : '当前筛选条件下没有用户'"
      />

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
.target-alert {
  margin-top: 12px;
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
