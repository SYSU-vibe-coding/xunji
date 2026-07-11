<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';

import StatusTag from '@/components/StatusTag.vue';
import { getItemReviewDetail, listItemReviews, reviewItem } from '@/api/admin';
import { ApiError, isUnauthorizedApiError } from '@/api/http';
import {
  type ItemReviewRecord,
  type ItemReviewDetail,
  categoryLabels,
  isConflictApiError,
} from '@xunji/shared';
import { shortDateTime } from '@/utils/format';
import { createLatestRequestGuard, lastPage, queryPositiveInt, queryValue } from '@/utils/admin-list';

const route = useRoute();
const router = useRouter();
const requestGuard = createLatestRequestGuard();

function normalizeBizType(value: unknown): 'LOST' | 'FOUND' | '' {
  if (value === 'lost' || value === 'LOST') return 'LOST';
  if (value === 'found' || value === 'FOUND') return 'FOUND';
  return '';
}

const list = ref<ItemReviewRecord[]>([]);
const total = ref(0);
const pageSize = 10;
const page = ref(queryPositiveInt(route.query.page));
const bizType = ref<'LOST' | 'FOUND' | ''>(normalizeBizType(route.query.bizType));
const targetId = ref(queryValue(route.query.targetId));
const loading = ref(true);
const errorMessage = ref('');
const actionLoadingId = ref('');
const drawerVisible = ref(false);
const detailLoading = ref(false);
const detailError = ref('');
const detail = ref<ItemReviewDetail | null>(null);

function currentQuery() {
  return {
    ...(bizType.value ? { bizType: bizType.value } : {}),
    ...(targetId.value ? { targetId: targetId.value } : {}),
    ...(!targetId.value && page.value > 1 ? { page: String(page.value) } : {}),
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
    if (targetId.value) {
      if (!bizType.value) {
        throw new Error('精确定位物品时缺少物品类型');
      }
      const data = await listItemReviews({
        pageNo: 1,
        pageSize: 1,
        bizType: bizType.value,
        targetId: targetId.value,
      });
      if (!requestGuard.isLatest(requestId)) return;
      list.value = data.list;
      total.value = data.total;
      if (data.list[0]) void openDetail(data.list[0]);
      return;
    }
    const data = await listItemReviews({
      pageNo: page.value,
      pageSize,
      bizType: (bizType.value || undefined) as 'LOST' | 'FOUND' | undefined,
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
    errorMessage.value = err instanceof ApiError || err instanceof Error
      ? err.message
      : '内容审核列表加载失败';
  } finally {
    if (requestGuard.isLatest(requestId)) loading.value = false;
  }
}

async function openDetail(record: Pick<ItemReviewRecord, 'id' | 'bizType'>) {
  drawerVisible.value = true;
  detailLoading.value = true;
  detailError.value = '';
  detail.value = null;
  try {
    detail.value = await getItemReviewDetail(record.bizType, record.id);
  } catch (err) {
    if (isUnauthorizedApiError(err)) return;
    detailError.value = err instanceof ApiError ? err.message : '审核详情加载失败';
  } finally {
    detailLoading.value = false;
  }
}

async function refreshAfterAction(record: Pick<ItemReviewRecord, 'id' | 'bizType'>) {
  await load();
  if (drawerVisible.value && detail.value?.id === record.id) await openDetail(record);
}

async function approve(record: Pick<ItemReviewRecord, 'id' | 'bizType' | 'itemName'>) {
  if (actionLoadingId.value) return;
  actionLoadingId.value = record.id;
  try {
    await ElMessageBox.confirm(
      `确认通过“${record.itemName}”的内容审核？通过后将进入正常业务流程。`,
      '确认通过审核',
      { type: 'warning', confirmButtonText: '确认通过', cancelButtonText: '取消' },
    );
    await reviewItem(record.bizType, record.id, { action: 'APPROVE' });
    ElMessage.success(`已通过 ${record.itemName}`);
    await refreshAfterAction(record);
  } catch (err) {
    if (err === 'cancel' || err === 'close') return;
    if (isConflictApiError(err)) {
      ElMessage.warning('审核状态已变化，已刷新最新数据');
      await refreshAfterAction(record);
      return;
    }
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  } finally {
    actionLoadingId.value = '';
  }
}

async function reject(record: Pick<ItemReviewRecord, 'id' | 'bizType' | 'itemName'>) {
  if (actionLoadingId.value) return;
  actionLoadingId.value = record.id;
  try {
    const result = await ElMessageBox.prompt(
      '请输入关闭原因。确认后物品将被关闭，且此操作不可撤销。',
      '确认关闭物品', {
      confirmButtonText: '确认关闭',
      cancelButtonText: '取消',
      inputValidator: (v) => (v && v.trim().length > 0) || '关闭原因不能为空',
      },
    );
    await reviewItem(record.bizType, record.id, { action: 'REJECT', comment: result.value.trim() });
    ElMessage.success(`已关闭 ${record.itemName}`);
    await refreshAfterAction(record);
  } catch (err) {
    if (err === 'cancel' || err === 'close') return;
    if (isConflictApiError(err)) {
      ElMessage.warning('审核状态已变化，已刷新最新数据');
      await refreshAfterAction(record);
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

function changeBizType() {
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
    const nextType = normalizeBizType(query.bizType);
    const nextTargetId = queryValue(query.targetId);
    const nextPage = queryPositiveInt(query.page);
    if (
      nextType === bizType.value &&
      nextTargetId === targetId.value &&
      nextPage === page.value
    ) return;
    bizType.value = nextType;
    targetId.value = nextTargetId;
    page.value = nextPage;
    void load();
  },
);

onMounted(load);
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="filter-card">
      <el-radio-group v-model="bizType" @change="changeBizType">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="FOUND">招领</el-radio-button>
        <el-radio-button label="LOST">失物</el-radio-button>
      </el-radio-group>
      <el-alert
        v-if="targetId"
        class="target-alert"
        type="info"
        :closable="false"
        :title="`正在精确定位目标 ${targetId}`"
      >
        <template #default><el-button link type="primary" @click="clearTarget">清除定位</el-button></template>
      </el-alert>
    </el-card>

    <el-card shadow="never">
      <el-result v-if="errorMessage" icon="error" title="内容审核列表加载失败" :sub-title="errorMessage">
        <template #extra><el-button type="primary" @click="load">重试</el-button></template>
      </el-result>
      <el-table v-else-if="loading || list.length" v-loading="loading" :data="list" stripe border style="width: 100%">
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
        <el-table-column label="操作" width="250" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDetail(row)">详情</el-button>
            <el-button
              type="primary"
              size="small"
              :disabled="row.reviewStatus !== 'PENDING'"
              :loading="actionLoadingId === row.id"
              @click="approve(row)"
            >
              通过
            </el-button>
            <el-button
              type="danger"
              plain
              size="small"
              :disabled="row.reviewStatus !== 'PENDING'"
              :loading="actionLoadingId === row.id"
              @click="reject(row)"
            >
              关闭
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty
        v-else
        :description="targetId ? `未找到目标 ${targetId}` : '当前筛选条件下没有待审核内容'"
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

    <el-drawer
      v-model="drawerVisible"
      title="内容审核详情"
      size="min(720px, 94vw)"
      destroy-on-close
    >
      <el-skeleton v-if="detailLoading" :rows="9" animated />
      <el-result v-else-if="detailError" icon="error" title="详情加载失败" :sub-title="detailError" />
      <div v-else-if="detail" class="review-detail">
        <div class="detail-heading">
          <div>
            <span class="eyebrow">{{ detail.bizType === 'FOUND' ? '招领信息' : '失物信息' }}</span>
            <h2>{{ detail.itemName }}</h2>
          </div>
          <StatusTag variant="review" :value="detail.reviewStatus" size="default" />
        </div>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="发布者">
            {{ detail.publisher.nickname }} · {{ detail.publisher.phone }}
          </el-descriptions-item>
          <el-descriptions-item label="类别">{{ categoryLabels[detail.category] }}</el-descriptions-item>
          <el-descriptions-item label="地点">
            {{ detail.foundLocation || detail.lostLocation || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="业务状态">{{ detail.status }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.foundTime" label="拾取时间">
            {{ detail.foundTime }}
          </el-descriptions-item>
          <el-descriptions-item v-if="detail.lostTimeStart" label="遗失时间">
            {{ detail.lostTimeStart }} 至 {{ detail.lostTimeEnd }}
          </el-descriptions-item>
          <el-descriptions-item label="审核状态">
            {{ detail.reviewStatus }}
          </el-descriptions-item>
          <el-descriptions-item label="审核意见">
            {{ detail.reviewComment || '暂无' }}
          </el-descriptions-item>
          <el-descriptions-item label="发布时间">{{ detail.createdAt }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ detail.updatedAt }}</el-descriptions-item>
        </el-descriptions>

        <section>
          <h3>描述</h3>
          <p class="description">{{ detail.description || '发布者未填写描述' }}</p>
        </section>

        <section>
          <h3>权限签名图片</h3>
          <div v-if="detail.imageUrls.length" class="image-grid">
            <el-image
              v-for="url in detail.imageUrls"
              :key="url"
              :src="url"
              :preview-src-list="detail.imageUrls"
              fit="cover"
              class="detail-image"
            />
          </div>
          <el-empty v-else description="未上传图片" :image-size="64" />
        </section>

        <section v-if="detail.bizType === 'FOUND'">
          <h3>验证问题</h3>
          <el-table v-if="detail.verifyQuestions?.length" :data="detail.verifyQuestions" border size="small">
            <el-table-column type="index" label="#" width="52" />
            <el-table-column prop="questionText" label="仅向认领人展示的问题" />
          </el-table>
          <el-empty v-else description="未设置验证问题" :image-size="64" />
        </section>
      </div>

      <template v-if="detail?.reviewStatus === 'PENDING'" #footer>
        <el-button
          type="danger"
          plain
          :loading="actionLoadingId === detail.id"
          @click="reject(detail)"
        >
          关闭并驳回
        </el-button>
        <el-button
          type="primary"
          :loading="actionLoadingId === detail.id"
          @click="approve(detail)"
        >
          通过审核
        </el-button>
      </template>
    </el-drawer>
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
.review-detail {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.detail-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  h2 {
    margin: 5px 0 0;
    font-size: 22px;
  }
}
.eyebrow {
  color: var(--xunji-text-muted);
  font-size: 12px;
  letter-spacing: 0.12em;
}
section h3 {
  margin: 0 0 10px;
  font-size: 15px;
}
.description {
  margin: 0;
  padding: 14px;
  border-radius: 8px;
  background: var(--xunji-bg);
  line-height: 1.7;
  white-space: pre-wrap;
}
.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}
.detail-image {
  width: 100%;
  height: 140px;
  border-radius: 8px;
}
</style>
