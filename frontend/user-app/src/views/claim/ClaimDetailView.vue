<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ArrowLeft } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';

import StatusTag from '@/components/StatusTag.vue';
import ImageUploader from '@/components/ImageUploader.vue';
import {
  appealClaim,
  confirmHandover,
  createHandover,
  getClaim,
  reviewClaim,
  submitClaimProofs,
} from '@/api/claim';
import { ApiError } from '@/api/http';
import { useAuthStore } from '@/stores/auth';
import {
  type ClaimDetail,
  type HandoverMethod,
  handoverMethodLabels,
  handoverMethodOptions,
  verifyLevelLabels,
} from '@xunji/shared';
import { shortDateTime, toBackendDateTime } from '@/utils/format';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const id = computed(() => route.params.id as string);
const detail = ref<ClaimDetail | null>(null);
const loading = ref(true);

const STAGES = ['PENDING', 'ANSWER_PASSED', 'PROOF_PENDING', 'APPROVED', 'HANDED_OVER'] as const;
const stageIndex = computed(() => {
  if (!detail.value) return 0;
  const i = STAGES.indexOf(detail.value.reviewStatus as (typeof STAGES)[number]);
  return i < 0 ? 0 : i;
});

const isClaimant = computed(() => detail.value?.claimantId === auth.profile?.id);

const proofForm = reactive({ proofImageUrls: [] as string[], proofText: '' });
const appealReason = ref('');
const handoverForm = reactive({
  method: 'MEETUP' as HandoverMethod,
  handoverLocation: '',
  handoverTime: null as Date | null,
});

const reviewing = ref(false);
const submittingProof = ref(false);
const appealing = ref(false);
const creatingHandover = ref(false);
const confirming = ref(false);

async function load() {
  loading.value = true;
  try {
    detail.value = await getClaim(id.value);
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '加载失败');
  } finally {
    loading.value = false;
  }
}

async function handleReview(action: 'APPROVE' | 'REJECT') {
  if (!detail.value) return;
  let comment = '';
  if (action === 'REJECT') {
    try {
      const result = await ElMessageBox.prompt('请输入驳回原因', '驳回认领', {
        confirmButtonText: '提交驳回',
        cancelButtonText: '取消',
        inputValidator: (v) => (v && v.trim().length > 0) || '驳回必须填写原因',
      });
      comment = result.value;
    } catch {
      return;
    }
  }
  reviewing.value = true;
  try {
    await reviewClaim(detail.value.id, { action, comment: comment || undefined });
    ElMessage.success(action === 'APPROVE' ? '已通过' : '已驳回');
    await load();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '处理失败');
  } finally {
    reviewing.value = false;
  }
}

async function submitProof() {
  if (!detail.value) return;
  if (!proofForm.proofImageUrls.length) {
    ElMessage.warning('请上传至少 1 张凭证图片');
    return;
  }
  submittingProof.value = true;
  try {
    await submitClaimProofs(detail.value.id, {
      proofImageUrls: proofForm.proofImageUrls,
      proofText: proofForm.proofText || undefined,
    });
    ElMessage.success('凭证已提交');
    proofForm.proofImageUrls = [];
    proofForm.proofText = '';
    await load();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '提交失败');
  } finally {
    submittingProof.value = false;
  }
}

async function submitAppeal() {
  if (!detail.value || !appealReason.value.trim()) {
    ElMessage.warning('请填写申诉理由');
    return;
  }
  appealing.value = true;
  try {
    await appealClaim(detail.value.id, { reason: appealReason.value.trim() });
    ElMessage.success('申诉已提交');
    appealReason.value = '';
    await load();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '提交失败');
  } finally {
    appealing.value = false;
  }
}

async function submitHandover() {
  if (!detail.value) return;
  if (!handoverForm.handoverLocation || !handoverForm.handoverTime) {
    ElMessage.warning('请填写交接地点与时间');
    return;
  }
  creatingHandover.value = true;
  try {
    await createHandover(detail.value.id, {
      method: handoverForm.method,
      handoverLocation: handoverForm.handoverLocation,
      handoverTime: toBackendDateTime(handoverForm.handoverTime),
    });
    ElMessage.success('交接已创建，请双方按时确认');
    await load();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '创建失败');
  } finally {
    creatingHandover.value = false;
  }
}

async function doConfirmHandover(role: 'OWNER' | 'FINDER') {
  if (!detail.value) return;
  confirming.value = true;
  try {
    await confirmHandover(detail.value.id, { role });
    ElMessage.success('已确认交接');
    await load();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  } finally {
    confirming.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="page">
    <el-button link @click="router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <el-skeleton v-if="loading" :rows="6" animated />

    <template v-else-if="detail">
      <el-card shadow="never" class="hero">
        <div class="hero-row">
          <div>
            <span class="eyebrow">CLAIM #{{ detail.id.slice(-8) }}</span>
            <h1>认领进度</h1>
          </div>
          <StatusTag variant="claim" :value="detail.reviewStatus" size="large" />
        </div>

        <el-steps :active="stageIndex" align-center finish-status="success" class="steps">
          <el-step title="待审核" description="提交申请" />
          <el-step title="问答通过" description="验证问题正确" />
          <el-step title="待补凭证" description="上传证明" />
          <el-step title="可交接" description="审核通过" />
          <el-step title="已交接" description="物品完成归还" />
        </el-steps>

        <el-descriptions :column="2" size="small" class="meta" border>
          <el-descriptions-item label="验证等级">{{ verifyLevelLabels[detail.verifyLevel] }}</el-descriptions-item>
          <el-descriptions-item label="申请时间">{{ shortDateTime(detail.claimedAt) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ shortDateTime(detail.updatedAt) }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.rejectReason" label="驳回原因">{{ detail.rejectReason }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 验证答题记录 -->
      <el-card v-if="detail.answers.length" shadow="never">
        <template #header><strong>验证问答</strong></template>
        <div v-for="a in detail.answers" :key="a.questionId" class="answer-row">
          <div class="q">{{ a.questionText }}</div>
          <div class="a">{{ a.answerText }}</div>
          <el-tag size="small" :type="a.matchScore >= 60 ? 'success' : 'warning'">
            匹配 {{ Math.round(a.matchScore) }}%
          </el-tag>
        </div>
      </el-card>

      <!-- 现有凭证 -->
      <el-card v-if="detail.proofImageUrls.length || detail.proofText" shadow="never">
        <template #header><strong>已上传凭证</strong></template>
        <p v-if="detail.proofText" class="proof-text">{{ detail.proofText }}</p>
        <div v-if="detail.proofImageUrls.length" class="proof-imgs">
          <el-image
            v-for="img in detail.proofImageUrls"
            :key="img"
            :src="img"
            :preview-src-list="detail.proofImageUrls"
            fit="cover"
            class="proof-img"
          />
        </div>
      </el-card>

      <!-- 拾获方审核（PENDING / ANSWER_PASSED / PROOF_PENDING） -->
      <el-card
        v-if="!isClaimant && ['PENDING', 'ANSWER_PASSED', 'PROOF_PENDING', 'APPEALING'].includes(detail.reviewStatus)"
        shadow="never"
        class="action-card"
      >
        <template #header><strong>审核操作</strong></template>
        <div class="actions">
          <el-button type="primary" :loading="reviewing" @click="handleReview('APPROVE')">
            通过认领
          </el-button>
          <el-button type="danger" plain :loading="reviewing" @click="handleReview('REJECT')">
            驳回
          </el-button>
        </div>
      </el-card>

      <!-- 认领人补交凭证（PROOF_PENDING） -->
      <el-card
        v-if="isClaimant && detail.reviewStatus === 'PROOF_PENDING'"
        shadow="never"
        class="action-card"
      >
        <template #header><strong>补交凭证</strong></template>
        <ImageUploader v-model="proofForm.proofImageUrls" biz-type="CLAIM_PROOF" :max="5" />
        <el-input
          v-model="proofForm.proofText"
          type="textarea"
          :rows="3"
          maxlength="500"
          show-word-limit
          placeholder="可补充文字说明"
          class="proof-input"
        />
        <el-button type="primary" :loading="submittingProof" @click="submitProof">
          提交凭证
        </el-button>
      </el-card>

      <!-- 认领人申诉（REJECTED） -->
      <el-card
        v-if="isClaimant && detail.reviewStatus === 'REJECTED'"
        shadow="never"
        class="action-card"
      >
        <template #header><strong>申诉</strong></template>
        <el-input
          v-model="appealReason"
          type="textarea"
          :rows="3"
          maxlength="500"
          show-word-limit
          placeholder="请说明申诉理由"
        />
        <el-button type="primary" :loading="appealing" @click="submitAppeal">
          提交申诉
        </el-button>
      </el-card>

      <!-- 交接（APPROVED 且尚未创建交接） -->
      <el-card
        v-if="!isClaimant && detail.reviewStatus === 'APPROVED' && !detail.handover"
        shadow="never"
        class="action-card"
      >
        <template #header><strong>安排交接</strong></template>
        <el-form label-position="top">
          <el-form-item label="交接方式">
            <el-select v-model="handoverForm.method">
              <el-option
                v-for="opt in handoverMethodOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="交接地点">
            <el-input v-model="handoverForm.handoverLocation" maxlength="100" placeholder="如：图书馆一楼服务台" />
          </el-form-item>
          <el-form-item label="交接时间">
            <el-date-picker
              v-model="handoverForm.handoverTime"
              type="datetime"
              format="YYYY-MM-DD HH:mm"
              placeholder="选择交接时间"
            />
          </el-form-item>
        </el-form>
        <el-button type="primary" :loading="creatingHandover" @click="submitHandover">
          创建交接
        </el-button>
      </el-card>

      <!-- 交接确认 -->
      <el-card v-if="detail.handover" shadow="never" class="handover-card">
        <template #header><strong>交接信息</strong></template>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="方式">{{ handoverMethodLabels[detail.handover.method] }}</el-descriptions-item>
          <el-descriptions-item label="地点">{{ detail.handover.handoverLocation }}</el-descriptions-item>
          <el-descriptions-item label="时间">{{ shortDateTime(detail.handover.handoverTime) }}</el-descriptions-item>
          <el-descriptions-item label="失主确认">
            <el-tag :type="detail.handover.ownerConfirmed ? 'success' : 'info'">
              {{ detail.handover.ownerConfirmed ? '已确认' : '待确认' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="拾获方确认">
            <el-tag :type="detail.handover.finderConfirmed ? 'success' : 'info'">
              {{ detail.handover.finderConfirmed ? '已确认' : '待确认' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <div class="actions" v-if="detail.reviewStatus === 'APPROVED'">
          <el-button
            v-if="isClaimant && !detail.handover.ownerConfirmed"
            type="primary"
            :loading="confirming"
            @click="doConfirmHandover('OWNER')"
          >
            我（失主）确认完成
          </el-button>
          <el-button
            v-if="!isClaimant && !detail.handover.finderConfirmed"
            type="primary"
            :loading="confirming"
            @click="doConfirmHandover('FINDER')"
          >
            我（拾获方）确认完成
          </el-button>
        </div>
      </el-card>
    </template>

    <el-empty v-else description="认领不存在或无访问权限" />
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.hero {
  .hero-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 18px;

    .eyebrow {
      color: var(--xunji-text-muted);
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }
    h1 {
      margin: 4px 0 0;
      font-size: 22px;
    }
  }
  .steps {
    margin-bottom: 18px;
  }
}

.answer-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--xunji-border);
  &:last-child {
    border-bottom: none;
  }
  .q {
    color: var(--xunji-text-muted);
    font-size: 13px;
  }
  .a {
    font-weight: 600;
  }
}

.proof-text {
  margin: 0 0 10px;
  color: var(--xunji-text);
  line-height: 1.6;
  font-size: 14px;
}
.proof-imgs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  .proof-img {
    width: 96px;
    height: 96px;
    border-radius: 10px;
    border: 1px solid var(--xunji-border);
  }
}

.action-card {
  .proof-input {
    margin: 12px 0;
  }
  .actions {
    display: flex;
    gap: 10px;
  }
}

.handover-card .actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

@media (max-width: 600px) {
  .answer-row {
    grid-template-columns: 1fr;
  }
}
</style>
