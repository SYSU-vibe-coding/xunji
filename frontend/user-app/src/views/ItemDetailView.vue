<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Lock, Picture as PictureIcon } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';

import EmptyState from '@/components/EmptyState.vue';
import ImageUploader from '@/components/ImageUploader.vue';
import StatusTag from '@/components/StatusTag.vue';
import {
  changeLostItemStatus,
  deleteLostItem,
  getFoundItem,
  getLostItem,
  reportItem,
} from '@/api/item';
import { createClaim } from '@/api/claim';
import { getMatch } from '@/api/match';
import { ApiError } from '@/api/http';
import { useAuthStore } from '@/stores/auth';
import {
  categoryLabels,
  contactPreferenceLabels,
  custodyTypeLabels,
  type FoundItemDetail,
  type LostItemDetail,
  type MatchDetail,
  isConflictApiError,
} from '@xunji/shared';
import { shortDateTime } from '@/utils/format';
import { buildClaimAnswers, canInitiateClaim } from '@/utils/interaction';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const bizType = computed(() => route.params.bizType as 'lost' | 'found');
const id = computed(() => route.params.id as string);

const foundDetail = ref<FoundItemDetail | null>(null);
const lostDetail = ref<LostItemDetail | null>(null);
const loading = ref(true);
const loadError = ref('');
const deleting = ref(false);
const statusChanging = ref(false);
const relatedMatch = ref<MatchDetail | null>(null);
const coverLoadFailed = ref(false);

const claimDialog = ref(false);
const claimAnswers = reactive<Record<string, string>>({});
const claimProofImageUrls = ref<string[]>([]);
const claimProofUploading = ref(false);
const claimProofUploadError = ref<string | null>(null);
const claimSubmitting = ref(false);
const reportDialog = ref(false);
const reportForm = reactive({ reason: '', description: '' });
const reportSubmitting = ref(false);

const isFound = computed(() => bizType.value === 'found');
const backendBizType = computed(() => (isFound.value ? 'FOUND' : 'LOST'));
const detail = computed(() => (isFound.value ? foundDetail.value : lostDetail.value));
const isOwner = computed(() => detail.value?.userId === auth.profile?.id);
const itemName = computed(() => detail.value?.itemName ?? '物品详情');
const images = computed(() => detail.value?.imageUrls ?? []);
const cover = computed(() => images.value[0] ?? null);
const creditFrozen = computed(() => !canInitiateClaim(auth.profile?.creditScore));
const canClaim = computed(() => Boolean(
  foundDetail.value &&
  !isOwner.value &&
  foundDetail.value.status === 'PENDING' &&
  foundDetail.value.reviewStatus === 'APPROVED' &&
  !foundDetail.value.hasActiveClaim &&
  !creditFrozen.value,
));

async function load() {
  loading.value = true;
  foundDetail.value = null;
  lostDetail.value = null;
  relatedMatch.value = null;
  loadError.value = '';
  coverLoadFailed.value = false;
  try {
    if (isFound.value) {
      foundDetail.value = await getFoundItem(id.value);
      foundDetail.value.verifyQuestions.forEach((q) => {
        if (claimAnswers[q.id] === undefined) claimAnswers[q.id] = '';
      });
    } else {
      lostDetail.value = await getLostItem(id.value);
    }
    const matchId = typeof route.query.matchId === 'string' ? route.query.matchId : '';
    if (matchId) {
      try {
        relatedMatch.value = await getMatch(matchId);
      } catch {
        relatedMatch.value = null;
      }
    }
  } catch (err) {
    loadError.value = err instanceof ApiError ? err.message : '加载失败，请稍后重试';
  } finally {
    loading.value = false;
  }
}

watch(() => route.fullPath, load);
onMounted(load);

async function handleDelete() {
  if (deleting.value || !lostDetail.value) return;
  try {
    await ElMessageBox.confirm('确认删除这条失物信息吗？', '删除确认', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
    });
  } catch {
    return;
  }
  deleting.value = true;
  try {
    await deleteLostItem(lostDetail.value.id);
    ElMessage.success('已删除');
    void router.push('/profile/items');
  } catch (err) {
    if (isConflictApiError(err)) {
      ElMessage.warning('物品状态已变化，已刷新最新详情');
      await load();
      return;
    }
    ElMessage.error(err instanceof ApiError ? err.message : '删除失败');
  } finally {
    deleting.value = false;
  }
}

async function changeLostStatus(status: 'FOUND' | 'CLOSED') {
  if (statusChanging.value || !lostDetail.value) return;
  const label = status === 'FOUND' ? '标记为已找回' : '结束寻物';
  try {
    await ElMessageBox.confirm(`确认${label}这条失物信息吗？`, label, {
      type: 'warning',
      confirmButtonText: label,
      cancelButtonText: '取消',
    });
  } catch {
    return;
  }
  statusChanging.value = true;
  try {
    await changeLostItemStatus(lostDetail.value.id, { status });
    ElMessage.success('状态已更新');
    await load();
  } catch (err) {
    if (isConflictApiError(err)) {
      ElMessage.warning('物品状态已变化，已关闭旧操作并刷新详情');
      await load();
      return;
    }
    ElMessage.error(err instanceof ApiError ? err.message : '状态更新失败');
  } finally {
    statusChanging.value = false;
  }
}

function openClaim() {
  if (!foundDetail.value) return;
  if (foundDetail.value.userId === auth.profile?.id) {
    ElMessage.warning('不能认领自己发布的招领');
    return;
  }
  if (creditFrozen.value) {
    ElMessage.warning('信用分低于 30，认领权限已冻结');
    return;
  }
  if (foundDetail.value.hasActiveClaim) {
    ElMessage.warning('该物品已有进行中的认领');
    return;
  }
  if (foundDetail.value.reviewStatus !== 'APPROVED') {
    ElMessage.warning('该招领尚未通过审核，暂不可认领');
    return;
  }
  Object.keys(claimAnswers).forEach((key) => delete claimAnswers[key]);
  foundDetail.value.verifyQuestions.forEach((q) => {
    claimAnswers[q.id] = '';
  });
  claimProofImageUrls.value = [];
  claimProofUploading.value = false;
  claimProofUploadError.value = null;
  claimDialog.value = true;
}

async function submitClaim() {
  if (claimSubmitting.value || !foundDetail.value) return;
  const answers = buildClaimAnswers(foundDetail.value.verifyQuestions, claimAnswers);
  if (!answers) {
    ElMessage.warning('请回答全部验证问题');
    return;
  }
  if (claimProofUploading.value) {
    ElMessage.warning('图片仍在上传，请稍候');
    return;
  }
  if (claimProofUploadError.value) {
    ElMessage.warning('有图片上传失败，请移除后重试');
    return;
  }
  claimSubmitting.value = true;
  try {
    const result = await createClaim({
      matchId: typeof route.query.matchId === 'string' ? route.query.matchId : null,
      foundItemId: foundDetail.value.id,
      answers,
      proofImageUrls: claimProofImageUrls.value,
    });
    ElMessage.success('认领申请已提交');
    claimDialog.value = false;
    void router.push(`/claims/${result.id}`);
  } catch (err) {
    if (isConflictApiError(err)) {
      claimDialog.value = false;
      ElMessage.warning('认领状态已变化，已关闭旧操作并刷新详情');
      await load();
      return;
    }
    ElMessage.error(err instanceof ApiError ? err.message : '提交失败');
  } finally {
    claimSubmitting.value = false;
  }
}

function openReport() {
  if (!detail.value) return;
  if (isOwner.value) {
    ElMessage.warning('不能举报自己发布的物品');
    return;
  }
  reportForm.reason = '';
  reportForm.description = '';
  reportDialog.value = true;
}

async function submitReport() {
  if (!detail.value) return;
  if (!reportForm.reason.trim()) {
    ElMessage.warning('请填写举报原因');
    return;
  }
  reportSubmitting.value = true;
  try {
    await reportItem(backendBizType.value, detail.value.id, {
      reason: reportForm.reason.trim(),
      description: reportForm.description.trim() || null,
    });
    ElMessage.success('举报已提交');
    reportDialog.value = false;
  } catch (err) {
    if (isConflictApiError(err)) {
      reportDialog.value = false;
      ElMessage.warning('举报或目标状态已变化，已关闭旧操作并刷新详情');
      await load();
      return;
    }
    ElMessage.error(err instanceof ApiError ? err.message : '提交举报失败');
  } finally {
    reportSubmitting.value = false;
  }
}

function goMatches() {
  if (!detail.value) return;
  void router.push({
    name: 'matches',
    query: { bizType: backendBizType.value, bizId: detail.value.id },
  });
}

function goClaim() {
  if (relatedMatch.value?.claimId) void router.push(`/claims/${relatedMatch.value.claimId}`);
}

function goManage() {
  if (!detail.value) return;
  void router.push({
    name: 'my-items',
    query: {
      tab: isFound.value ? 'found' : 'lost',
      page: '1',
      bizType: backendBizType.value,
      id: detail.value.id,
    },
  });
}
</script>

<template>
  <div class="page">
    <el-skeleton v-if="loading" :rows="6" animated />

    <template v-else-if="detail">
      <el-card shadow="never" class="hero-card" :body-style="{ padding: 0 }">
        <div class="hero-grid">
          <div class="media">
            <img v-if="cover && !coverLoadFailed" :src="cover" :alt="itemName" @error="coverLoadFailed = true" />
            <div v-else-if="coverLoadFailed" class="placeholder image-error">
              <el-icon :size="40"><PictureIcon /></el-icon>
              <span>图片加载失败，链接可能已过期</span>
              <el-button link type="primary" @click="load">重新加载图片</el-button>
            </div>
            <div v-else-if="isFound && foundDetail?.isSensitive" class="sensitive">
              <el-icon :size="40"><Lock /></el-icon>
              <strong>敏感物品原图已隐藏</strong>
              <small>仅发布者和管理员可查看原图</small>
            </div>
            <div v-else class="placeholder">
              <el-icon :size="40"><PictureIcon /></el-icon>
            </div>
            <div v-if="images.length > 1" class="thumbs">
              <img v-for="img in images" :key="img" :src="img" :alt="itemName" />
            </div>
          </div>
          <div class="info">
            <div class="badges">
              <el-tag round effect="dark">{{ categoryLabels[detail.category] }}</el-tag>
              <StatusTag :variant="bizType" :value="detail.status" />
              <StatusTag variant="review" :value="detail.reviewStatus" />
              <StatusTag
                v-if="relatedMatch?.claimStatus"
                variant="claim"
                :value="relatedMatch.claimStatus"
              />
            </div>
            <h1>{{ detail.itemName }}</h1>
            <p class="desc">{{ detail.description || '发布者未填写描述' }}</p>

            <el-descriptions :column="1" border size="small" class="meta">
              <template v-if="isFound">
                <el-descriptions-item label="拾获时间">{{ shortDateTime(foundDetail!.foundTime) }}</el-descriptions-item>
                <el-descriptions-item label="拾获地点">{{ foundDetail!.foundLocation }}</el-descriptions-item>
                <el-descriptions-item label="保管方式">{{ custodyTypeLabels[foundDetail!.custodyType] }}</el-descriptions-item>
                <el-descriptions-item label="联系偏好">{{ contactPreferenceLabels[foundDetail!.contactPreference] }}</el-descriptions-item>
              </template>
              <template v-else>
                <el-descriptions-item label="丢失时间">
                  {{ shortDateTime(lostDetail!.lostTimeStart) }} ~ {{ shortDateTime(lostDetail!.lostTimeEnd) }}
                </el-descriptions-item>
                <el-descriptions-item label="丢失地点">{{ lostDetail!.lostLocation }}</el-descriptions-item>
                <el-descriptions-item label="订阅匹配">
                  {{ lostDetail!.subscribeMatch ? '已订阅' : '未订阅' }}
                </el-descriptions-item>
                <el-descriptions-item v-if="isOwner" label="匹配数">{{ lostDetail!.matchCount ?? 0 }}</el-descriptions-item>
              </template>
              <el-descriptions-item label="发布时间">{{ shortDateTime(detail.createdAt) }}</el-descriptions-item>
              <el-descriptions-item label="审核状态">
                <StatusTag variant="review" :value="detail.reviewStatus" />
              </el-descriptions-item>
              <el-descriptions-item label="审核意见">{{ detail.reviewComment || '暂无' }}</el-descriptions-item>
            </el-descriptions>

            <div class="actions">
              <el-button v-if="isOwner" @click="goMatches">查看匹配</el-button>
              <el-button v-if="relatedMatch?.claimId" type="primary" plain @click="goClaim">
                查看认领进度
              </el-button>
              <el-button v-if="!isOwner" plain @click="openReport">举报</el-button>
              <template v-if="isFound">
                <el-button v-if="isOwner" type="primary" @click="goManage">管理 / 编辑发布</el-button>
                <el-button
                  type="primary"
                  size="large"
                  v-if="canClaim"
                  @click="openClaim"
                >
                  发起认领
                </el-button>
              </template>
              <template v-else-if="isOwner">
                <el-button @click="goManage">管理 / 编辑发布</el-button>
                <el-button
                  type="success"
                  plain
                  :disabled="lostDetail!.status !== 'SEARCHING'"
                  :loading="statusChanging"
                  @click="changeLostStatus('FOUND')"
                >
                  标记已找回
                </el-button>
                <el-button
                  type="warning"
                  plain
                  :disabled="lostDetail!.status !== 'SEARCHING'"
                  :loading="statusChanging"
                  @click="changeLostStatus('CLOSED')"
                >
                  结束寻物
                </el-button>
                <el-button type="danger" plain :loading="deleting" @click="handleDelete">删除</el-button>
              </template>
            </div>
          </div>
        </div>
      </el-card>
    </template>

    <EmptyState
      v-else-if="loadError"
      title="物品详情加载失败"
      :description="loadError"
      action-text="重试"
      @action="load"
    />
    <el-empty v-else description="物品不存在或已下架" />

    <!-- 认领对话框 -->
    <el-dialog
      v-model="claimDialog"
      title="发起认领"
      width="520px"
      :close-on-click-modal="false"
    >
      <p class="dialog-tip">
        请如实回答验证问题。回答正确后，发布者会进入下一步审核。
      </p>
      <template v-if="foundDetail?.verifyQuestions?.length">
        <el-form label-position="top">
          <el-form-item
            v-for="q in foundDetail.verifyQuestions"
            :key="q.id"
            :label="q.questionText"
          >
            <el-input v-model="claimAnswers[q.id]" placeholder="请输入答案" maxlength="200" />
          </el-form-item>
        </el-form>
      </template>
      <el-alert
        v-else
        type="info"
        :closable="false"
        title="该招领无验证问题，提交后等待发布者人工核对"
      />
      <el-form label-position="top" class="proof-form">
        <el-form-item label="凭证图片">
          <ImageUploader
            v-model="claimProofImageUrls"
            biz-type="CLAIM_PROOF"
            :max="5"
            @uploading-change="claimProofUploading = $event"
            @error-change="claimProofUploadError = $event"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="claimSubmitting" @click="claimDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="claimSubmitting"
          :disabled="claimProofUploading || Boolean(claimProofUploadError)"
          @click="submitClaim"
        >
          提交认领
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="reportDialog" title="举报物品" width="480px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="举报原因" required>
          <el-input v-model="reportForm.reason" maxlength="100" placeholder="例如：虚假发布、信息不实" />
        </el-form-item>
        <el-form-item label="详细说明">
          <el-input
            v-model="reportForm.description"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reportDialog = false">取消</el-button>
        <el-button type="primary" :loading="reportSubmitting" @click="submitReport">
          提交举报
        </el-button>
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

.hero-card {
  overflow: hidden;
}

.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 1.4fr);

  .media {
    background: linear-gradient(135deg, #ecfeff, #ede9fe);
    min-height: 360px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 16px;

    img {
      width: 100%;
      height: 100%;
      max-height: 420px;
      object-fit: cover;
      border-radius: 12px;
    }

    .placeholder,
    .sensitive {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      color: var(--xunji-text-muted);

      strong {
        color: var(--xunji-text);
        font-size: 15px;
      }
      small {
        font-size: 12px;
      }
    }

    .thumbs {
      display: flex;
      gap: 6px;
      margin-top: 10px;
      flex-wrap: wrap;

      img {
        width: 52px;
        height: 52px;
        border-radius: 8px;
        object-fit: cover;
        border: 1px solid var(--xunji-border);
      }
    }
  }

  .info {
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 14px;

    .badges {
      display: flex;
      gap: 8px;
    }
    h1 {
      margin: 0;
      font-size: 24px;
    }
    .desc {
      margin: 0;
      color: var(--xunji-text-muted);
      font-size: 14px;
      line-height: 1.6;
    }
    .actions {
      display: flex;
      gap: 10px;
      margin-top: 4px;
    }
  }
}

.dialog-tip {
  margin: 0 0 12px;
  color: var(--xunji-text-muted);
  font-size: 13px;
}

@media (max-width: 880px) {
  .hero-grid {
    grid-template-columns: 1fr;
  }
  .media {
    min-height: 220px;
  }

  .info .actions {
    flex-direction: column;

    .el-button {
      width: 100%;
      margin-left: 0;
    }
  }
}
</style>
