<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';

import EmptyState from '@/components/EmptyState.vue';
import ImageUploader from '@/components/ImageUploader.vue';
import ItemCard from '@/components/ItemCard.vue';
import PageHeader from '@/components/PageHeader.vue';
import StatusTag from '@/components/StatusTag.vue';
import {
  deleteLostItem,
  getFoundItem,
  getLostItem,
  listFoundItems,
  listLostItems,
  updateLostItem,
} from '@/api/item';
import { ApiError } from '@/api/http';
import { useAuthStore } from '@/stores/auth';
import {
  categoryLabels,
  categoryOptions,
  contactPreferenceLabels,
  custodyTypeLabels,
  type FoundItemDetail,
  type FoundItemSummary,
  type ItemCategory,
  type LostItemDetail,
  type LostItemSummary,
} from '@xunji/shared';
import { shortDateTime, toBackendDateTime } from '@/utils/format';

const router = useRouter();
const auth = useAuthStore();

const tab = ref<'lost' | 'found'>('lost');
const lostList = ref<LostItemSummary[]>([]);
const foundList = ref<FoundItemSummary[]>([]);
const loading = ref(true);

async function load() {
  loading.value = true;
  if (!auth.profile) await auth.loadProfile().catch(() => {});
  try {
    const [lostPage, foundPage] = await Promise.all([
      listLostItems({ pageSize: 50, includeClosed: true }),
      listFoundItems({ pageSize: 50, includeClosed: true }),
    ]);
    const myId = auth.profile?.id ?? '';
    lostList.value = lostPage.list.filter((it) => it.userId === myId);
    foundList.value = foundPage.list.filter((it) => it.userId === myId);
  } catch (err) {
    if (err instanceof ApiError && err.code === 40002) return;
    lostList.value = [];
    foundList.value = [];
  } finally {
    loading.value = false;
  }
}

const visibleList = computed(() => (tab.value === 'lost' ? lostList.value : foundList.value));

watch(tab, () => {
  /* tab 切换不重新拉取，只过滤已加载的数据 */
});

onMounted(load);

// 响应式弹窗宽度：手机视口铺满，平板/桌面用固定宽
const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1024);
function onResize() {
  viewportWidth.value = window.innerWidth;
}
onMounted(() => window.addEventListener('resize', onResize));
onUnmounted(() => window.removeEventListener('resize', onResize));
const dialogWidth = computed(() => (viewportWidth.value < 720 ? '94vw' : '640px'));
const isMobile = computed(() => viewportWidth.value < 720);

// ---------- 弹窗 ----------

const dialogVisible = ref(false);
const dialogLoading = ref(false);
const dialogKind = ref<'lost' | 'found'>('lost');
const lostDetail = ref<LostItemDetail | null>(null);
const foundDetail = ref<FoundItemDetail | null>(null);

const editing = ref(false);
const saving = ref(false);
const deleting = ref(false);
const formRef = ref<FormInstance>();

const editForm = reactive({
  itemName: '',
  category: 'ELECTRONIC' as ItemCategory,
  lostRange: [] as Date[],
  lostLocation: '',
  description: '',
  subscribeMatch: true,
  imageUrls: [] as string[],
});

const rules: FormRules = {
  itemName: [
    { required: true, message: '请输入物品名称' },
    { min: 1, max: 100, message: '物品名称 1-100 字' },
  ],
  category: [{ required: true, message: '请选择物品类别' }],
  lostRange: [
    {
      required: true,
      validator: (_rule, value: unknown[]) => {
        if (!value || value.length !== 2) return Promise.reject('请选择丢失时间区间');
        return Promise.resolve();
      },
    },
  ],
  lostLocation: [
    { required: true, message: '请输入丢失地点' },
    { max: 100, message: '地点不超过 100 字' },
  ],
  description: [{ max: 500, message: '描述不超过 500 字' }],
};

function resetEditForm(detail: LostItemDetail) {
  editForm.itemName = detail.itemName;
  editForm.category = detail.category;
  editForm.lostRange = [new Date(detail.lostTimeStart), new Date(detail.lostTimeEnd)];
  editForm.lostLocation = detail.lostLocation;
  editForm.description = detail.description ?? '';
  editForm.subscribeMatch = detail.subscribeMatch;
  editForm.imageUrls = [...detail.imageUrls];
}

async function openCard(id: string, kind: 'lost' | 'found') {
  dialogKind.value = kind;
  dialogVisible.value = true;
  dialogLoading.value = true;
  editing.value = false;
  lostDetail.value = null;
  foundDetail.value = null;
  try {
    if (kind === 'lost') {
      const detail = await getLostItem(id);
      lostDetail.value = detail;
      resetEditForm(detail);
    } else {
      foundDetail.value = await getFoundItem(id);
    }
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '加载失败');
    dialogVisible.value = false;
  } finally {
    dialogLoading.value = false;
  }
}

function startEdit() {
  if (!lostDetail.value) return;
  resetEditForm(lostDetail.value);
  editing.value = true;
}

function cancelEdit() {
  if (lostDetail.value) resetEditForm(lostDetail.value);
  editing.value = false;
}

async function saveEdit() {
  if (!lostDetail.value) return;
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  saving.value = true;
  try {
    const updated = await updateLostItem(lostDetail.value.id, {
      itemName: editForm.itemName,
      category: editForm.category,
      description: editForm.description || null,
      lostTimeStart: toBackendDateTime(editForm.lostRange[0]),
      lostTimeEnd: toBackendDateTime(editForm.lostRange[1]),
      lostLocation: editForm.lostLocation,
      subscribeMatch: editForm.subscribeMatch,
      imageUrls: editForm.imageUrls,
    });
    lostDetail.value = updated;
    resetEditForm(updated);
    editing.value = false;
    ElMessage.success('已保存');
    await load();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '保存失败');
  } finally {
    saving.value = false;
  }
}

async function handleDelete() {
  if (!lostDetail.value) return;
  try {
    await ElMessageBox.confirm(
      `确认删除「${lostDetail.value.itemName}」？此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' },
    );
  } catch {
    return;
  }
  deleting.value = true;
  try {
    await deleteLostItem(lostDetail.value.id);
    ElMessage.success('已删除');
    dialogVisible.value = false;
    await load();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '删除失败');
  } finally {
    deleting.value = false;
  }
}

const detailImages = computed(() => {
  if (dialogKind.value === 'lost') return lostDetail.value?.imageUrls ?? [];
  return foundDetail.value?.imageUrls ?? [];
});
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="My posts"
      title="我的发布"
      description="点击卡片查看详情，失物可在弹窗内编辑或删除"
      back-fallback="/profile"
    />

    <el-radio-group v-model="tab" size="large">
      <el-radio-button label="lost">失物 ({{ lostList.length }})</el-radio-button>
      <el-radio-button label="found">招领 ({{ foundList.length }})</el-radio-button>
    </el-radio-group>

    <el-skeleton v-if="loading" :rows="4" animated />
    <template v-else>
      <div v-if="visibleList.length" class="grid">
        <ItemCard
          v-for="item in visibleList"
          :key="item.id"
          :kind="tab === 'lost' ? 'lost' : 'found'"
          :item="item"
          @open="(id) => openCard(id, tab)"
        />
      </div>
      <EmptyState
        v-else
        :title="tab === 'lost' ? '还没有发布过失物' : '还没有发布过招领'"
        action-text="去发布"
        @action="router.push(tab === 'lost' ? '/publish/lost' : '/publish/found')"
      />
    </template>

    <!-- 详情 / 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogKind === 'lost' ? '失物详情' : '招领详情'"
      :width="dialogWidth"
      :top="isMobile ? '6vh' : '15vh'"
      class="detail-dialog"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-skeleton v-if="dialogLoading" :rows="6" animated />

      <!-- ===== 失物 ===== -->
      <template v-else-if="dialogKind === 'lost' && lostDetail">
        <!-- 查看模式 -->
        <div v-if="!editing" class="detail">
          <div class="badges">
            <el-tag round effect="dark">{{ categoryLabels[lostDetail.category] }}</el-tag>
            <StatusTag variant="lost" :value="lostDetail.status" />
          </div>
          <h3 class="title">{{ lostDetail.itemName }}</h3>
          <p class="desc">{{ lostDetail.description || '发布者未填写描述' }}</p>

          <div v-if="detailImages.length" class="thumbs">
            <img v-for="img in detailImages" :key="img" :src="img" :alt="lostDetail.itemName" />
          </div>

          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="丢失时间">
              {{ shortDateTime(lostDetail.lostTimeStart) }} ~ {{ shortDateTime(lostDetail.lostTimeEnd) }}
            </el-descriptions-item>
            <el-descriptions-item label="丢失地点">{{ lostDetail.lostLocation }}</el-descriptions-item>
            <el-descriptions-item label="订阅匹配">
              {{ lostDetail.subscribeMatch ? '已订阅' : '未订阅' }}
            </el-descriptions-item>
            <el-descriptions-item label="匹配数">{{ lostDetail.matchCount ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="发布时间">{{ shortDateTime(lostDetail.createdAt) }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 编辑模式 -->
        <el-form
          v-else
          ref="formRef"
          :model="editForm"
          :rules="rules"
          label-position="top"
        >
          <el-form-item label="物品名称" prop="itemName">
            <el-input v-model="editForm.itemName" maxlength="100" />
          </el-form-item>
          <el-form-item label="物品类别" prop="category">
            <el-select v-model="editForm.category" style="width: 100%">
              <el-option
                v-for="opt in categoryOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="丢失时间区间" prop="lostRange">
            <el-date-picker
              v-model="editForm.lostRange"
              type="datetimerange"
              range-separator="至"
              start-placeholder="开始时间"
              end-placeholder="结束时间"
              format="YYYY-MM-DD HH:mm"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="丢失地点" prop="lostLocation">
            <el-input v-model="editForm.lostLocation" maxlength="100" />
          </el-form-item>
          <el-form-item label="物品描述" prop="description">
            <el-input
              v-model="editForm.description"
              type="textarea"
              :rows="4"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
          <el-form-item label="物品图片（最多 5 张）">
            <ImageUploader v-model="editForm.imageUrls" biz-type="LOST" :max="5" />
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="editForm.subscribeMatch">
              订阅匹配提醒，发现相似招领自动通知
            </el-checkbox>
          </el-form-item>
        </el-form>
      </template>

      <!-- ===== 招领（只读） ===== -->
      <template v-else-if="dialogKind === 'found' && foundDetail">
        <div class="detail">
          <div class="badges">
            <el-tag round effect="dark">{{ categoryLabels[foundDetail.category] }}</el-tag>
            <StatusTag variant="found" :value="foundDetail.status" />
          </div>
          <h3 class="title">{{ foundDetail.itemName }}</h3>
          <p class="desc">{{ foundDetail.description || '发布者未填写描述' }}</p>

          <div v-if="!foundDetail.isSensitive && detailImages.length" class="thumbs">
            <img v-for="img in detailImages" :key="img" :src="img" :alt="foundDetail.itemName" />
          </div>
          <el-alert
            v-else-if="foundDetail.isSensitive"
            type="warning"
            :closable="false"
            title="敏感物品，原图仅完成实名认证的失主可见"
          />

          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="拾获时间">{{ shortDateTime(foundDetail.foundTime) }}</el-descriptions-item>
            <el-descriptions-item label="拾获地点">{{ foundDetail.foundLocation }}</el-descriptions-item>
            <el-descriptions-item label="保管方式">{{ custodyTypeLabels[foundDetail.custodyType] }}</el-descriptions-item>
            <el-descriptions-item label="联系偏好">{{ contactPreferenceLabels[foundDetail.contactPreference] }}</el-descriptions-item>
            <el-descriptions-item label="发布时间">{{ shortDateTime(foundDetail.createdAt) }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </template>

      <template #footer>
        <!-- 失物：查看 → 编辑 / 删除 / 关闭 ；编辑 → 取消 / 保存 -->
        <template v-if="dialogKind === 'lost' && lostDetail">
          <template v-if="!editing">
            <el-button type="danger" plain :loading="deleting" @click="handleDelete">
              删除
            </el-button>
            <el-button type="primary" @click="startEdit">编辑</el-button>
            <el-button @click="dialogVisible = false">关闭</el-button>
          </template>
          <template v-else>
            <el-button @click="cancelEdit">取消</el-button>
            <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
          </template>
        </template>
        <!-- 招领：仅关闭 -->
        <el-button v-else @click="dialogVisible = false">关闭</el-button>
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
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
  // 防止任意子元素的长内容（描述、URL）撑破弹窗
  min-width: 0;
  word-break: break-word;
  overflow-wrap: anywhere;

  .badges {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .title {
    margin: 0;
    font-size: 20px;
    word-break: break-word;
  }
  .desc {
    margin: 0;
    color: var(--xunji-text-muted);
    font-size: 14px;
    line-height: 1.6;
    word-break: break-word;
  }
  .thumbs {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;

    img {
      width: 88px;
      height: 88px;
      border-radius: 8px;
      object-fit: cover;
      border: 1px solid var(--xunji-border);
    }
  }
}
</style>

<style lang="scss">
/* 非 scoped：el-dialog 通过 teleport 渲染到 body，scoped 选不中 */
.detail-dialog {
  // 让 body 在小屏内容超长时纵向滚动，而不是横向溢出
  .el-dialog__body {
    max-height: 70vh;
    overflow-y: auto;
    overflow-x: hidden;
    padding-top: 12px;
  }

  // descriptions / 表单内长内容自动换行
  .el-descriptions__cell,
  .el-descriptions__label,
  .el-descriptions__content {
    word-break: break-word;
  }

  // 表单内所有控件都不超过容器宽
  .el-form-item__content,
  .el-input,
  .el-select,
  .el-date-editor,
  .el-textarea,
  .el-input__wrapper {
    max-width: 100%;
    width: 100%;
    box-sizing: border-box;
  }

  // datetimerange 在窄屏会被两个时间输入挤出去：允许内容换行 + 缩小内边距
  .el-date-editor.el-input__wrapper {
    flex-wrap: wrap;
  }
}

@media (max-width: 720px) {
  .detail-dialog {
    .el-dialog__body {
      padding-left: 16px;
      padding-right: 16px;
    }
    // 底部按钮在窄屏纵向铺满，避免横排被挤出
    .el-dialog__footer {
      display: flex;
      flex-direction: column-reverse;
      gap: 8px;
      .el-button {
        width: 100%;
        margin-left: 0 !important;
      }
    }
    // datetimerange 在窄屏改竖向，避免左右溢出
    .el-date-editor--datetimerange {
      .el-range-input {
        min-width: 0;
      }
    }
  }
}
</style>
