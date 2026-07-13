<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';

import StatusTag from '@/components/StatusTag.vue';
import { getAdminClaimDetail, listAdminClaims, reviewClaimAppeal } from '@/api/admin';
import { ApiError, isUnauthorizedApiError } from '@/api/http';
import { createLatestRequestGuard, lastPage, queryPositiveInt, queryValue } from '@/utils/admin-list';
import { shortDateTime } from '@/utils/format';
import {
  type AdminClaimDetail,
  type AdminClaimRecord,
  type ClaimReviewStatus,
  type ClaimVerificationSource,
  categoryLabels,
  claimStatusLabels,
  contactPreferenceLabels,
  custodyTypeLabels,
  handoverMethodLabels,
  isConflictApiError,
  verifyLevelLabels,
} from '@xunji/shared';

const route = useRoute();
const router = useRouter();
const requestGuard = createLatestRequestGuard();
const statuses: ClaimReviewStatus[] = [
  'PENDING',
  'ANSWER_PASSED',
  'PROOF_PENDING',
  'APPROVED',
  'REJECTED',
  'APPEALING',
  'HANDED_OVER',
  'TERMINATED',
];
type StatusFilter = ClaimReviewStatus | '';
const verificationSourceLabels: Record<ClaimVerificationSource, string> = {
  TEXT_MODEL: '小模型语义校验',
  KEYWORD_RULES: '关键词规则',
  NOT_REQUIRED: '无需问答',
  LEGACY_UNKNOWN: '历史记录',
};

function routeStatus(value: unknown): StatusFilter {
  return statuses.includes(value as ClaimReviewStatus) ? value as ClaimReviewStatus : '';
}

function verificationSourceLabel(source: ClaimVerificationSource): string {
  return verificationSourceLabels[source];
}

const list = ref<AdminClaimRecord[]>([]);
const total = ref(0);
const pageSize = 10;
const page = ref(queryPositiveInt(route.query.page));
const reviewStatus = ref<StatusFilter>(routeStatus(route.query.reviewStatus));
const loading = ref(true);
const errorMessage = ref('');
const actionLoadingIds = ref(new Set<string>());

const drawerVisible = ref(false);
const detailLoading = ref(false);
const detailError = ref('');
const detail = ref<AdminClaimDetail | null>(null);

function currentQuery(targetId = queryValue(route.query.targetId)) {
  return {
    ...(reviewStatus.value ? { reviewStatus: reviewStatus.value } : {}),
    ...(page.value > 1 ? { page: String(page.value) } : {}),
    ...(targetId ? { targetId } : {}),
  };
}

async function syncUrl(targetId = queryValue(route.query.targetId)) {
  await router.replace({ query: currentQuery(targetId) });
}

async function load() {
  const requestId = requestGuard.next();
  loading.value = true;
  errorMessage.value = '';
  try {
    const data = await listAdminClaims({
      ...(reviewStatus.value ? { reviewStatus: reviewStatus.value } : {}),
      pageNo: page.value,
      pageSize,
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
    errorMessage.value = err instanceof ApiError ? err.message : '认领列表加载失败';
  } finally {
    if (requestGuard.isLatest(requestId)) loading.value = false;
  }
}

async function openDetail(id: string, updateUrl = true) {
  drawerVisible.value = true;
  detailLoading.value = true;
  detailError.value = '';
  detail.value = null;
  if (updateUrl) await syncUrl(id);
  try {
    detail.value = await getAdminClaimDetail(id);
  } catch (err) {
    if (isUnauthorizedApiError(err)) return;
    detailError.value = err instanceof ApiError ? err.message : '认领详情加载失败';
  } finally {
    detailLoading.value = false;
  }
}

async function closeDetail() {
  detail.value = null;
  detailError.value = '';
  if (route.query.targetId) await syncUrl('');
}

async function refreshAfterAction(id: string) {
  await load();
  if (drawerVisible.value && detail.value?.id === id) await openDetail(id, false);
}

async function approve(record: Pick<AdminClaimRecord, 'id' | 'item'>) {
  if (actionLoadingIds.value.has(record.id)) return;
  actionLoadingIds.value.add(record.id);
  try {
    await ElMessageBox.confirm(
      `确认申诉成立并通过“${record.item.itemName}”的认领？确认后将进入交接流程。`,
      '确认通过认领申诉',
      { type: 'warning', confirmButtonText: '确认通过', cancelButtonText: '取消' },
    );
    await reviewClaimAppeal(record.id, { action: 'APPROVE', comment: '申诉材料核验通过' });
    ElMessage.success('认领申诉已通过');
    await refreshAfterAction(record.id);
  } catch (err) {
    if (err === 'cancel' || err === 'close') return;
    if (isConflictApiError(err)) {
      ElMessage.warning('申诉状态已变化，已刷新最新数据');
      await refreshAfterAction(record.id);
      return;
    }
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  } finally {
    actionLoadingIds.value.delete(record.id);
  }
}

async function reject(record: Pick<AdminClaimRecord, 'id' | 'item'>) {
  if (actionLoadingIds.value.has(record.id)) return;
  actionLoadingIds.value.add(record.id);
  try {
    const result = await ElMessageBox.prompt(
      '请输入维持驳回的原因。确认后该申诉将被驳回。',
      '确认驳回认领申诉',
      {
        confirmButtonText: '确认驳回',
        cancelButtonText: '取消',
        inputValidator: (value) => (value && value.trim().length > 0) || '驳回原因不能为空',
      },
    );
    await reviewClaimAppeal(record.id, { action: 'REJECT', comment: result.value.trim() });
    ElMessage.success('认领申诉已驳回');
    await refreshAfterAction(record.id);
  } catch (err) {
    if (err === 'cancel' || err === 'close') return;
    if (isConflictApiError(err)) {
      ElMessage.warning('申诉状态已变化，已刷新最新数据');
      await refreshAfterAction(record.id);
      return;
    }
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  } finally {
    actionLoadingIds.value.delete(record.id);
  }
}

async function filter() {
  page.value = 1;
  await syncUrl('');
  await load();
}

async function changePage() {
  await syncUrl();
  await load();
}

watch(
  () => route.query,
  (query) => {
    const nextPage = queryPositiveInt(query.page);
    const nextStatus = routeStatus(query.reviewStatus);
    const nextTarget = queryValue(query.targetId);
    const currentTarget = detail.value?.id ?? '';
    if (nextPage !== page.value || nextStatus !== reviewStatus.value) {
      page.value = nextPage;
      reviewStatus.value = nextStatus;
      void load();
    }
    if (
      nextTarget &&
      nextTarget !== currentTarget &&
      !(drawerVisible.value && detailLoading.value)
    ) void openDetail(nextTarget, false);
  },
);

onMounted(() => {
  void load();
  const targetId = queryValue(route.query.targetId);
  if (targetId) void openDetail(targetId, false);
});
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="filter-card">
      <div class="filter-field">
        <span>认领状态</span>
        <el-select
          v-model="reviewStatus"
          class="status-select"
          placeholder="全部状态"
          @change="filter"
        >
          <el-option label="全部状态" value="" />
          <el-option
            v-for="status in statuses"
            :key="status"
            :label="claimStatusLabels[status]"
            :value="status"
          />
        </el-select>
      </div>
      <span class="result-count">共 {{ total }} 条</span>
    </el-card>

    <el-card shadow="never">
      <el-result v-if="errorMessage" icon="error" title="认领列表加载失败" :sub-title="errorMessage">
        <template #extra><el-button type="primary" @click="load">重试</el-button></template>
      </el-result>
      <el-table v-else-if="loading || list.length" v-loading="loading" :data="list" stripe border>
        <el-table-column label="物品" min-width="155">
          <template #default="{ row }">
            <el-link type="primary" underline="never" @click="openDetail(row.id)">
              {{ row.item.itemName }}
            </el-link>
            <div class="muted">{{ categoryLabels[row.item.category as keyof typeof categoryLabels] }}</div>
          </template>
        </el-table-column>
        <el-table-column label="认领人" min-width="125">
          <template #default="{ row }">
            <strong>{{ row.claimant.nickname }}</strong>
            <div class="muted">{{ row.claimant.phone }}</div>
          </template>
        </el-table-column>
        <el-table-column label="发布者" min-width="125">
          <template #default="{ row }">
            <strong>{{ row.finder.nickname }}</strong>
            <div class="muted">{{ row.finder.phone }}</div>
          </template>
        </el-table-column>
        <el-table-column label="验证方式" width="105">
          <template #default="{ row }">
            {{ verifyLevelLabels[row.verifyLevel as keyof typeof verifyLevelLabels] }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><StatusTag variant="claim" :value="row.reviewStatus" /></template>
        </el-table-column>
        <el-table-column label="时间" width="140">
          <template #default="{ row }">
            <div>{{ shortDateTime(row.claimedAt) }}</div>
            <div v-if="row.updatedAt !== row.claimedAt" class="muted">
              更新 {{ shortDateTime(row.updatedAt) }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190" align="center" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDetail(row.id)">详情</el-button>
            <template v-if="row.reviewStatus === 'APPEALING'">
              <el-button
                type="primary"
                size="small"
                :loading="actionLoadingIds.has(row.id)"
                @click="approve(row)"
              >
                通过
              </el-button>
              <el-button
                type="danger"
                plain
                size="small"
                :loading="actionLoadingIds.has(row.id)"
                @click="reject(row)"
              >
                驳回
              </el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="当前筛选条件下没有认领记录" />

      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        background
        class="pagination"
        @current-change="changePage"
      />
    </el-card>

    <el-drawer
      v-model="drawerVisible"
      title="认领详情"
      size="min(760px, 94vw)"
      destroy-on-close
      @closed="closeDetail"
    >
      <el-skeleton v-if="detailLoading" :rows="8" animated />
      <el-result v-else-if="detailError" icon="error" title="详情加载失败" :sub-title="detailError">
        <template #extra>
          <el-button type="primary" @click="openDetail(queryValue(route.query.targetId), false)">重试</el-button>
        </template>
      </el-result>
      <div v-else-if="detail" class="detail">
        <div class="detail-heading">
          <div>
            <span class="eyebrow">{{ detail.id }}</span>
            <h2>{{ detail.item.itemName }}</h2>
          </div>
          <StatusTag variant="claim" :value="detail.reviewStatus" size="default" />
        </div>

        <el-alert
          v-if="detail.rejectReason"
          type="error"
          :closable="false"
          :title="`驳回原因：${detail.rejectReason}`"
        />
        <el-alert
          v-if="detail.appealReason"
          type="warning"
          :closable="false"
          :title="`申诉理由：${detail.appealReason}`"
        />

        <el-descriptions :column="2" border>
          <el-descriptions-item label="验证级别">{{ verifyLevelLabels[detail.verifyLevel] }}</el-descriptions-item>
          <el-descriptions-item label="校验引擎">
            <el-tag :type="detail.verificationDegraded ? 'warning' : 'success'" effect="plain">
              {{ verificationSourceLabel(detail.verificationSource) }}
              {{ detail.verificationDegraded ? ' · 已降级' : '' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="物品状态">{{ detail.item.status }}</el-descriptions-item>
          <el-descriptions-item label="内容审核">{{ detail.item.reviewStatus }}</el-descriptions-item>
          <el-descriptions-item label="认领人">
            {{ detail.claimant.nickname }} · {{ detail.claimant.phone }}
          </el-descriptions-item>
          <el-descriptions-item label="发布者">
            {{ detail.finder.nickname }} · {{ detail.finder.phone }}
          </el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ detail.claimedAt }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ detail.updatedAt }}</el-descriptions-item>
          <el-descriptions-item label="匹配记录">{{ detail.matchId || '无关联匹配' }}</el-descriptions-item>
          <el-descriptions-item label="招领编号">{{ detail.foundItemId }}</el-descriptions-item>
        </el-descriptions>

        <section>
          <h3>招领物品</h3>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="分类">{{ categoryLabels[detail.item.category] }}</el-descriptions-item>
            <el-descriptions-item label="拾获时间">{{ detail.item.foundTime }}</el-descriptions-item>
            <el-descriptions-item label="拾获地点" :span="2">{{ detail.item.foundLocation }}</el-descriptions-item>
            <el-descriptions-item label="保管方式">
              {{ custodyTypeLabels[detail.item.custodyType] }}
            </el-descriptions-item>
            <el-descriptions-item label="联系偏好">
              {{ contactPreferenceLabels[detail.item.contactPreference] }}
            </el-descriptions-item>
            <el-descriptions-item label="物品描述" :span="2">
              {{ detail.item.description || '未填写' }}
            </el-descriptions-item>
          </el-descriptions>
        </section>

        <section>
          <h3>验证问答</h3>
          <el-table v-if="detail.answers.length" :data="detail.answers" border size="small">
            <el-table-column prop="questionText" label="发布者问题" min-width="160" />
            <el-table-column label="发布者参考答案" min-width="180">
              <template #default="{ row }">
                <div v-if="row.referenceAnswers.length" class="reference-list">
                  <el-tag v-for="answer in row.referenceAnswers" :key="answer" type="info" effect="plain">
                    {{ answer }}
                  </el-tag>
                </div>
                <span v-else class="muted">未记录</span>
              </template>
            </el-table-column>
            <el-table-column prop="answerText" label="认领人回答" min-width="160" />
            <el-table-column label="答案匹配度" width="120">
              <template #default="{ row }">
                <div v-if="row.matchScore !== null" class="score-cell">
                  <el-progress
                    :percentage="Math.round(row.matchScore)"
                    :stroke-width="6"
                    :show-text="false"
                  />
                  <span>{{ row.matchScore.toFixed(1) }}%</span>
                </div>
                <span v-else>—</span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="未提交验证问答" :image-size="64" />
        </section>

        <section>
          <h3>补充凭证</h3>
          <p v-if="detail.proofText" class="proof-text">{{ detail.proofText }}</p>
          <div v-if="detail.proofImageUrls.length" class="proof-grid">
            <el-image
              v-for="url in detail.proofImageUrls"
              :key="url"
              :src="url"
              :preview-src-list="detail.proofImageUrls"
              fit="cover"
              class="proof-image"
            />
          </div>
          <el-empty v-else-if="!detail.proofText" description="未提交补充凭证" :image-size="64" />
        </section>

        <section>
          <h3>交接进度</h3>
          <el-descriptions v-if="detail.handover" :column="2" border>
            <el-descriptions-item label="交接方式">
              {{ handoverMethodLabels[detail.handover.method] }}
            </el-descriptions-item>
            <el-descriptions-item label="交接时间">{{ detail.handover.handoverTime }}</el-descriptions-item>
            <el-descriptions-item label="交接地点" :span="2">
              {{ detail.handover.handoverLocation }}
            </el-descriptions-item>
            <el-descriptions-item label="认领人确认">
              <el-tag :type="detail.handover.ownerConfirmed ? 'success' : 'info'">
                {{ detail.handover.ownerConfirmed ? '已确认' : '未确认' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="发布者确认">
              <el-tag :type="detail.handover.finderConfirmed ? 'success' : 'info'">
                {{ detail.handover.finderConfirmed ? '已确认' : '未确认' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="完成时间" :span="2">
              {{ detail.handover.completedAt || '尚未完成' }}
            </el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="尚未创建交接安排" :image-size="64" />
        </section>
      </div>

      <template v-if="detail?.reviewStatus === 'APPEALING'" #footer>
        <el-button
          type="danger"
          plain
          :loading="actionLoadingIds.has(detail.id)"
          @click="reject(detail)"
        >
          驳回申诉
        </el-button>
        <el-button
          type="primary"
          :loading="actionLoadingIds.has(detail.id)"
          @click="approve(detail)"
        >
          通过申诉
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
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
}
.filter-field {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--xunji-text-muted);
}
.status-select {
  width: 160px;
}
.result-count {
  margin-left: auto;
  color: var(--xunji-text-muted);
  font-size: 13px;
}
.muted,
.eyebrow {
  color: var(--xunji-text-muted);
  font-size: 12px;
}
.pagination {
  margin-top: 14px;
  justify-content: center;
}
.detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.detail-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  h2 {
    margin: 5px 0 0;
    font-size: 22px;
  }
}
section h3 {
  margin: 0 0 10px;
  font-size: 15px;
}
.reference-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.score-cell {
  display: grid;
  grid-template-columns: minmax(48px, 1fr) 42px;
  align-items: center;
  gap: 8px;
  font-variant-numeric: tabular-nums;

  :deep(.el-progress) {
    width: 100%;
  }
}
.proof-text {
  margin: 0 0 10px;
  padding: 12px;
  border-radius: 8px;
  background: var(--xunji-bg);
  line-height: 1.6;
}
.proof-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
}
.proof-image {
  width: 100%;
  height: 120px;
  border-radius: 8px;
}
@media (max-width: 720px) {
  .filter-card :deep(.el-card__body) {
    align-items: stretch;
  }
  .filter-field {
    flex: 1;
  }
  .status-select {
    flex: 1;
    width: auto;
  }
  :deep(.el-descriptions__body .el-descriptions__table) {
    min-width: 540px;
  }
}
</style>
