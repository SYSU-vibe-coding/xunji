<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Aim, Refresh, View } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

import EmptyState from '@/components/EmptyState.vue';
import ImageUploader from '@/components/ImageUploader.vue';
import StatusTag from '@/components/StatusTag.vue';
import { createClaim } from '@/api/claim';
import { getFoundItem } from '@/api/item';
import { getMatch, listMatches, recalculateMatch } from '@/api/match';
import { ApiError } from '@/api/http';
import {
  categoryLabels,
  type FoundItemDetail,
  type MatchDetail,
  type MatchSummary,
} from '@xunji/shared';
import { shortDateTime } from '@/utils/format';

const route = useRoute();
const router = useRouter();

const bizType = computed(() => {
  const value = route.query.bizType;
  return value === 'LOST' || value === 'FOUND' ? value : null;
});
const bizId = computed(() => {
  const value = route.query.bizId;
  return typeof value === 'string' && value ? value : null;
});
const hasContext = computed(() => Boolean(bizType.value && bizId.value));

const matches = ref<MatchSummary[]>([]);
const total = ref(0);
const loading = ref(false);
const pageNo = ref(1);
const pageSize = ref(20);
const recalculating = ref(false);
const detailVisible = ref(false);
const activeMatch = ref<MatchDetail | MatchSummary | null>(null);

const claimDialog = ref(false);
const claimFoundDetail = ref<FoundItemDetail | null>(null);
const claimAnswers = reactive<Record<string, string>>({});
const proofImageUrls = ref<string[]>([]);
const claimSubmitting = ref(false);

const title = computed(() => (bizType.value === 'FOUND' ? '招领匹配' : bizType.value === 'LOST' ? '失物匹配' : '我的匹配'));

async function load() {
  loading.value = true;
  try {
    const params: Record<string, unknown> = {
      pageNo: pageNo.value,
      pageSize: pageSize.value,
      minScore: 70,
    };
    if (bizType.value && bizId.value) {
      params.bizType = bizType.value;
      params.bizId = bizId.value;
    }
    const data = await listMatches(params);
    matches.value = data.list;
    total.value = data.total;
  } catch (err) {
    matches.value = [];
    ElMessage.error(err instanceof ApiError ? err.message : '加载匹配失败');
  } finally {
    loading.value = false;
  }
}

async function openMatch(matchId: string) {
  try {
    activeMatch.value = await getMatch(matchId);
    detailVisible.value = true;
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '加载匹配详情失败');
  }
}

async function handleRecalculate() {
  const currentBizType = bizType.value;
  const currentBizId = bizId.value;
  if (!currentBizType || !currentBizId) {
    ElMessage.info('请在具体物品详情页使用重算功能');
    return;
  }
  recalculating.value = true;
  try {
    const result = await recalculateMatch({ bizType: currentBizType, bizId: currentBizId });
    ElMessage.success(`已提交重算任务，预计 ${result.estimatedCount ?? 0} 条`);
    await load();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '提交重算失败');
  } finally {
    recalculating.value = false;
  }
}

function openCounterpart(match: MatchSummary) {
  const kind = bizType.value === 'FOUND' ? 'lost' : 'found';
  void router.push(`/items/${kind}/${match.counterpart.id}`);
}

async function openClaim(match: MatchSummary) {
  try {
    let claimMatch: MatchDetail | MatchSummary = match;
    if (match.canClaim === undefined) {
      claimMatch = await getMatch(match.matchId);
    }
    if (!claimMatch.canClaim) {
      ElMessage.warning('当前匹配暂不可认领');
      return;
    }
    claimFoundDetail.value = await getFoundItem(claimMatch.foundItemId);
    claimFoundDetail.value.verifyQuestions.forEach((q) => {
      if (claimAnswers[q.id] === undefined) claimAnswers[q.id] = '';
    });
    activeMatch.value = claimMatch;
    proofImageUrls.value = [];
    claimDialog.value = true;
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '加载认领信息失败');
  }
}

async function submitClaim() {
  if (!activeMatch.value || !claimFoundDetail.value) return;
  const answers = claimFoundDetail.value.verifyQuestions
    .map((q) => ({ questionId: q.id, answerText: (claimAnswers[q.id] ?? '').trim() }))
    .filter((a) => a.answerText);
  claimSubmitting.value = true;
  try {
    const result = await createClaim({
      matchId: activeMatch.value.matchId,
      foundItemId: activeMatch.value.foundItemId,
      answers,
      proofImageUrls: proofImageUrls.value,
    });
    ElMessage.success('认领申请已提交');
    claimDialog.value = false;
    detailVisible.value = false;
    void router.push(`/claims/${result.id}`);
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '提交认领失败');
  } finally {
    claimSubmitting.value = false;
  }
}

function onPageChange(p: number) {
  pageNo.value = p;
  load();
}

watch(() => route.fullPath, load);
onMounted(load);
</script>

<template>
  <div class="page">
    <header class="page-header">
      <span class="eyebrow">Matches</span>
      <h1>{{ title }}</h1>
      <p>查看系统推荐的相似物品，并从高可信匹配直接发起认领。</p>
      <div v-if="hasContext" class="header-actions">
        <el-button :loading="recalculating" :icon="Refresh" @click="handleRecalculate">
          重新计算
        </el-button>
      </div>
    </header>

    <el-skeleton v-if="loading" :rows="4" animated />

    <template v-else>
      <div v-if="matches.length" class="grid">
        <el-card v-for="m in matches" :key="m.matchId" shadow="never" class="match-card">
          <div class="match-head">
            <div>
              <strong>{{ m.counterpart.itemName }}</strong>
              <p>{{ categoryLabels[m.counterpart.category] }} · {{ m.counterpart.location }}</p>
            </div>
            <StatusTag variant="match" :value="m.matchStatus" />
          </div>
          <el-progress :percentage="Math.round(m.totalScore)" :stroke-width="8" />
          <div class="score-row">
            <span>图像 {{ Math.round(m.imageScore) }}</span>
            <span>文本 {{ Math.round(m.textScore) }}</span>
            <span>地点 {{ Math.round(m.locationScore) }}</span>
            <span>时间 {{ Math.round(m.timeScore) }}</span>
          </div>
          <div class="meta">{{ shortDateTime(m.counterpart.time) }}</div>
          <div class="actions">
            <el-button :icon="View" @click="openMatch(m.matchId)">详情</el-button>
            <el-button type="primary" :disabled="m.canClaim === false" @click="openClaim(m)">
              发起认领
            </el-button>
          </div>
        </el-card>
      </div>
      <EmptyState
        v-else
        title="暂无匹配结果"
        description="系统还未生成匹配记录，可稍后刷新或联系管理员触发匹配。"
      >
        <template #icon><Aim /></template>
      </EmptyState>

      <div v-if="total > pageSize" class="pager">
        <el-pagination
          background
          layout="prev, pager, next"
          :total="total"
          :current-page="pageNo"
          :page-size="pageSize"
          @current-change="onPageChange"
        />
      </div>
    </template>

    <el-dialog v-model="detailVisible" title="匹配详情" width="560px">
      <template v-if="activeMatch">
        <div class="detail">
          <div class="detail-title">
            <strong>{{ activeMatch.counterpart.itemName }}</strong>
            <el-progress type="circle" :percentage="Math.round(activeMatch.totalScore)" :width="72" />
          </div>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="匹配状态">
              <StatusTag variant="match" :value="activeMatch.matchStatus" />
            </el-descriptions-item>
            <el-descriptions-item label="地点">{{ activeMatch.counterpart.location }}</el-descriptions-item>
            <el-descriptions-item label="时间">{{ shortDateTime(activeMatch.counterpart.time) }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ shortDateTime(activeMatch.createdAt) }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </template>
      <template #footer>
        <el-button v-if="activeMatch" @click="openCounterpart(activeMatch)">查看物品</el-button>
        <el-button
          v-if="activeMatch"
          type="primary"
          :disabled="activeMatch.canClaim === false"
          @click="openClaim(activeMatch)"
        >
          发起认领
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="claimDialog" title="发起认领" width="560px" :close-on-click-modal="false">
      <template v-if="claimFoundDetail">
        <el-form label-position="top">
          <el-form-item
            v-for="q in claimFoundDetail.verifyQuestions"
            :key="q.id"
            :label="q.questionText"
          >
            <el-input v-model="claimAnswers[q.id]" maxlength="200" />
          </el-form-item>
          <el-form-item label="凭证图片">
            <ImageUploader v-model="proofImageUrls" biz-type="CLAIM_PROOF" :max="5" />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="claimDialog = false">取消</el-button>
        <el-button type="primary" :loading="claimSubmitting" @click="submitClaim">
          提交认领
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-header {
  display: flex;
  flex-direction: column;
  gap: 8px;

  .eyebrow {
    color: var(--xunji-text-muted);
    font-size: 12px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }
  h1,
  p {
    margin: 0;
  }
  h1 {
    font-size: 22px;
  }
  p {
    color: var(--xunji-text-muted);
    font-size: 13px;
  }
}

.header-actions {
  margin-top: 4px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.match-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.match-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;

  p {
    margin: 4px 0 0;
    color: var(--xunji-text-muted);
    font-size: 12px;
  }
}

.score-row,
.meta {
  color: var(--xunji-text-muted);
  font-size: 12px;
}

.score-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
}

.actions {
  display: flex;
  gap: 8px;
}

.pager {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}

.detail {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.detail-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

@media (max-width: 720px) {
  .actions {
    flex-direction: column;
  }
}
</style>
