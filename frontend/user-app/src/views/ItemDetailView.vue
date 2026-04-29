<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ArrowLeft, Lock, Picture as PictureIcon } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';

import StatusTag from '@/components/StatusTag.vue';
import {
  deleteLostItem,
  getFoundItem,
  getLostItem,
} from '@/api/item';
import { createClaim } from '@/api/claim';
import { ApiError } from '@/api/http';
import { useAuthStore } from '@/stores/auth';
import {
  categoryLabels,
  contactPreferenceLabels,
  custodyTypeLabels,
  type FoundItemDetail,
  type LostItemDetail,
} from '@xunji/shared';
import { shortDateTime } from '@/utils/format';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const bizType = computed(() => route.params.bizType as 'lost' | 'found');
const id = computed(() => route.params.id as string);

const foundDetail = ref<FoundItemDetail | null>(null);
const lostDetail = ref<LostItemDetail | null>(null);
const loading = ref(true);

const claimDialog = ref(false);
const claimAnswers = reactive<Record<string, string>>({});
const claimSubmitting = ref(false);

const isFound = computed(() => bizType.value === 'found');
const detail = computed(() => (isFound.value ? foundDetail.value : lostDetail.value));
const isOwner = computed(() => detail.value?.userId === auth.profile?.id);
const itemName = computed(() => detail.value?.itemName ?? '物品详情');
const images = computed(() => detail.value?.imageUrls ?? []);
const cover = computed(() => images.value[0] ?? null);

async function load() {
  loading.value = true;
  foundDetail.value = null;
  lostDetail.value = null;
  try {
    if (isFound.value) {
      foundDetail.value = await getFoundItem(id.value);
      foundDetail.value.verifyQuestions.forEach((q) => {
        if (claimAnswers[q.id] === undefined) claimAnswers[q.id] = '';
      });
    } else {
      lostDetail.value = await getLostItem(id.value);
    }
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '加载失败');
  } finally {
    loading.value = false;
  }
}

watch(() => route.fullPath, load);
onMounted(load);

async function handleDelete() {
  if (!lostDetail.value) return;
  try {
    await ElMessageBox.confirm('确认删除这条失物信息吗？', '删除确认', { type: 'warning' });
  } catch {
    return;
  }
  try {
    await deleteLostItem(lostDetail.value.id);
    ElMessage.success('已删除');
    void router.push('/profile/items');
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '删除失败');
  }
}

function openClaim() {
  if (!foundDetail.value) return;
  if (foundDetail.value.userId === auth.profile?.id) {
    ElMessage.warning('不能认领自己发布的招领');
    return;
  }
  claimDialog.value = true;
}

async function submitClaim() {
  if (!foundDetail.value) return;
  const answers = foundDetail.value.verifyQuestions
    .map((q) => ({ questionId: q.id, answerText: (claimAnswers[q.id] ?? '').trim() }))
    .filter((a) => a.answerText);
  claimSubmitting.value = true;
  try {
    const result = await createClaim({
      foundItemId: foundDetail.value.id,
      answers,
    });
    ElMessage.success('认领申请已提交');
    claimDialog.value = false;
    void router.push(`/claims/${result.id}`);
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '提交失败');
  } finally {
    claimSubmitting.value = false;
  }
}
</script>

<template>
  <div class="page">
    <el-button link @click="router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <el-skeleton v-if="loading" :rows="6" animated />

    <template v-else-if="detail">
      <el-card shadow="never" class="hero-card" :body-style="{ padding: 0 }">
        <div class="hero-grid">
          <div class="media">
            <div v-if="isFound && foundDetail?.isSensitive" class="sensitive">
              <el-icon :size="40"><Lock /></el-icon>
              <strong>敏感物品已脱敏</strong>
              <small>仅完成实名认证的失主可见原图</small>
            </div>
            <img v-else-if="cover" :src="cover" :alt="itemName" />
            <div v-else class="placeholder">
              <el-icon :size="40"><PictureIcon /></el-icon>
            </div>
            <div v-if="images.length > 1 && !(isFound && foundDetail?.isSensitive)" class="thumbs">
              <img v-for="img in images" :key="img" :src="img" :alt="itemName" />
            </div>
          </div>
          <div class="info">
            <div class="badges">
              <el-tag round effect="dark">{{ categoryLabels[detail.category] }}</el-tag>
              <StatusTag :variant="bizType" :value="detail.status" />
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
            </el-descriptions>

            <div class="actions">
              <template v-if="isFound">
                <el-button
                  type="primary"
                  size="large"
                  :disabled="isOwner || foundDetail!.status !== 'PENDING'"
                  @click="openClaim"
                >
                  发起认领
                </el-button>
              </template>
              <template v-else-if="isOwner">
                <el-button @click="router.push('/profile/items')">编辑 / 删除</el-button>
                <el-button type="danger" plain @click="handleDelete">删除</el-button>
              </template>
            </div>
          </div>
        </div>
      </el-card>
    </template>

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
}
</style>
