<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormItemRule,
  type FormRules,
} from 'element-plus';

import EmptyState from '@/components/EmptyState.vue';
import ImageUploader from '@/components/ImageUploader.vue';
import ItemCard from '@/components/ItemCard.vue';
import PageHeader from '@/components/PageHeader.vue';
import StatusTag from '@/components/StatusTag.vue';
import {
  changeFoundItemStatus,
  changeLostItemStatus,
  getFoundItem,
  getLostItem,
  listMyFoundItems,
  listMyLostItems,
  updateFoundItem,
  updateLostItem,
} from '@/api/item';
import { ApiError, isAuthApiError } from '@/api/http';
import {
  categoryLabels,
  categoryOptions,
  contactOptions,
  contactPreferenceLabels,
  custodyOptions,
  custodyTypeLabels,
  type ContactPreference,
  type CustodyType,
  type FoundItemDetail,
  type FoundItemSummary,
  type ItemCategory,
  type LostItemDetail,
  type LostItemSummary,
  isConflictApiError,
} from '@xunji/shared';
import { shortDateTime, toBackendDateTime } from '@/utils/format';
import {
  buildMyItemsQuery,
  parseMyItemsQuery,
  parseVerifyQuestionDrafts,
  type MyItemsTab,
  type VerifyQuestionDraft,
  type VerifyQuestionFieldErrors,
} from '@/utils/interaction';

const route = useRoute();
const router = useRouter();
const initialQuery = parseMyItemsQuery(route.query);
const pageSize = 12;

const tab = ref<MyItemsTab>(initialQuery.tab);
const lostList = ref<LostItemSummary[]>([]);
const foundList = ref<FoundItemSummary[]>([]);
const lostPage = ref(initialQuery.tab === 'lost' ? initialQuery.page : 1);
const foundPage = ref(initialQuery.tab === 'found' ? initialQuery.page : 1);
const lostTotal = ref(0);
const foundTotal = ref(0);
const listLoading = reactive({ lost: false, found: false });
const listError = reactive({ lost: '', found: '' });
const visibleList = computed(() => (tab.value === 'lost' ? lostList.value : foundList.value));
const visiblePage = computed(() => (tab.value === 'lost' ? lostPage.value : foundPage.value));
const visibleTotal = computed(() => (tab.value === 'lost' ? lostTotal.value : foundTotal.value));
const visibleLoading = computed(() => listLoading[tab.value]);
const visibleError = computed(() => listError[tab.value]);

async function syncUrl(targetId = '', replace = false) {
  const target = {
    name: 'my-items',
    query: buildMyItemsQuery(tab.value, visiblePage.value, targetId),
  };
  if (router.resolve(target).fullPath === route.fullPath) return;
  await (replace ? router.replace(target) : router.push(target));
}

async function loadKind(kind: MyItemsTab) {
  listLoading[kind] = true;
  listError[kind] = '';
  try {
    if (kind === 'lost') {
      const data = await listMyLostItems({
        pageNo: lostPage.value,
        pageSize,
        includeClosed: true,
      });
      lostList.value = data.list;
      lostTotal.value = data.total;
      const finalPage = Math.max(1, Math.ceil(data.total / pageSize));
      if (lostPage.value > finalPage) {
        lostPage.value = finalPage;
        if (tab.value === kind) await syncUrl('', true);
        await loadKind(kind);
      }
    } else {
      const data = await listMyFoundItems({
        pageNo: foundPage.value,
        pageSize,
        includeClosed: true,
      });
      foundList.value = data.list;
      foundTotal.value = data.total;
      const finalPage = Math.max(1, Math.ceil(data.total / pageSize));
      if (foundPage.value > finalPage) {
        foundPage.value = finalPage;
        if (tab.value === kind) await syncUrl('', true);
        await loadKind(kind);
      }
    }
  } catch (err) {
    if (isAuthApiError(err)) return;
    listError[kind] = err instanceof ApiError ? err.message : '加载我的发布失败';
  } finally {
    listLoading[kind] = false;
  }
}

async function changeTab() {
  await syncUrl();
  if (!listLoading[tab.value]) await loadKind(tab.value);
}

async function changePage(page: number) {
  if (tab.value === 'lost') lostPage.value = page;
  else foundPage.value = page;
  await syncUrl();
  await loadKind(tab.value);
}

const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1024);
function onResize() {
  viewportWidth.value = window.innerWidth;
}
onMounted(() => window.addEventListener('resize', onResize));
onUnmounted(() => window.removeEventListener('resize', onResize));
const dialogWidth = computed(() => (viewportWidth.value < 720 ? '94vw' : '680px'));
const isMobile = computed(() => viewportWidth.value < 720);

const dialogVisible = ref(false);
const dialogLoading = ref(false);
const dialogKind = ref<'lost' | 'found'>('lost');
const lostDetail = ref<LostItemDetail | null>(null);
const foundDetail = ref<FoundItemDetail | null>(null);
const editing = ref(false);
const saving = ref(false);
const imageUploading = ref(false);
const imageUploadError = ref<string | null>(null);
const changingStatus = ref(false);
const formRef = ref<FormInstance>();
const foundQuestionMode = ref<'KEEP' | 'REPLACE'>('KEEP');
const foundQuestions = ref<VerifyQuestionDraft[]>([{ questionText: '', answerKeywords: '' }]);
const questionErrors = ref<Record<number, VerifyQuestionFieldErrors>>({});
const canCloseFound = computed(
  () => foundDetail.value?.status === 'PENDING' || foundDetail.value?.status === 'CLAIMING',
);
const hasLegacyLostImages = computed(() => Boolean(
  lostDetail.value?.imageUrls.length && !lostDetail.value.imageRefs?.length,
));
const hasLegacyFoundImages = computed(() => Boolean(
  foundDetail.value?.imageUrls.length && !foundDetail.value.imageRefs?.length,
));
const needsLegacyImageReplacement = computed(() => (
  dialogKind.value === 'lost'
    ? hasLegacyLostImages.value && !lostForm.imageUrls.length
    : hasLegacyFoundImages.value && !foundForm.imageUrls.length
));

const lostForm = reactive({
  itemName: '',
  category: 'ELECTRONIC' as ItemCategory,
  lostRange: [] as Date[],
  lostLocation: '',
  description: '',
  subscribeMatch: true,
  imageUrls: [] as string[],
});

const foundForm = reactive({
  itemName: '',
  category: 'CERT' as ItemCategory,
  foundTime: null as Date | null,
  foundLocation: '',
  custodyType: 'SECURITY' as CustodyType,
  contactPreference: 'IN_APP' as ContactPreference,
  description: '',
  imageUrls: [] as string[],
});

const commonRules: FormRules = {
  itemName: [
    { required: true, message: '请输入物品名称' },
    { min: 1, max: 100, message: '物品名称 1-100 字' },
  ],
  category: [{ required: true, message: '请选择物品类别' }],
  description: [{ max: 500, message: '描述不超过 500 字' }],
};

const lostRules: FormRules = {
  ...commonRules,
  lostRange: [
    {
      required: true,
      validator: (_rule: FormItemRule, value: unknown) => {
        if (!Array.isArray(value) || value.length !== 2) return Promise.reject('请选择丢失时间区间');
        return Promise.resolve();
      },
    },
  ],
  lostLocation: [
    { required: true, message: '请输入丢失地点' },
    { max: 100, message: '地点不超过 100 字' },
  ],
};

const foundRules: FormRules = {
  ...commonRules,
  foundTime: [{ required: true, message: '请选择拾获时间' }],
  foundLocation: [
    { required: true, message: '请输入拾获地点' },
    { max: 100, message: '地点不超过 100 字' },
  ],
  custodyType: [{ required: true, message: '请选择保管方式' }],
  contactPreference: [{ required: true, message: '请选择联系方式偏好' }],
};

function resetLostForm(detail: LostItemDetail) {
  lostForm.itemName = detail.itemName;
  lostForm.category = detail.category;
  lostForm.lostRange = [new Date(detail.lostTimeStart), new Date(detail.lostTimeEnd)];
  lostForm.lostLocation = detail.lostLocation;
  lostForm.description = detail.description ?? '';
  lostForm.subscribeMatch = detail.subscribeMatch;
  lostForm.imageUrls = [...(detail.imageRefs ?? [])];
}

function resetFoundForm(detail: FoundItemDetail) {
  foundForm.itemName = detail.itemName;
  foundForm.category = detail.category;
  foundForm.foundTime = new Date(detail.foundTime);
  foundForm.foundLocation = detail.foundLocation;
  foundForm.custodyType = detail.custodyType;
  foundForm.contactPreference = detail.contactPreference;
  foundForm.description = detail.description ?? '';
  foundForm.imageUrls = [...(detail.imageRefs ?? [])];
  foundQuestionMode.value = 'KEEP';
  foundQuestions.value = [{ questionText: '', answerKeywords: '' }];
  questionErrors.value = {};
}

async function openCard(id: string, kind: MyItemsTab) {
  if (dialogLoading.value && dialogKind.value === kind) return;
  dialogKind.value = kind;
  dialogVisible.value = true;
  dialogLoading.value = true;
  editing.value = false;
  lostDetail.value = null;
  foundDetail.value = null;
  imageUploading.value = false;
  imageUploadError.value = null;
  try {
    if (kind === 'lost') {
      const detail = await getLostItem(id);
      lostDetail.value = detail;
      resetLostForm(detail);
    } else {
      const detail = await getFoundItem(id);
      foundDetail.value = detail;
      resetFoundForm(detail);
    }
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '加载详情失败');
    dialogVisible.value = false;
  } finally {
    dialogLoading.value = false;
  }
}

async function openFromCard(id: string, kind: MyItemsTab) {
  tab.value = kind;
  const target = { name: 'my-items', query: buildMyItemsQuery(kind, visiblePage.value, id) };
  if (router.resolve(target).fullPath === route.fullPath) await openCard(id, kind);
  else await router.push(target);
}

function closeDetailRoute() {
  const target = parseMyItemsQuery(route.query);
  if (target.targetId) void syncUrl('', true);
}

function startEdit() {
  if (dialogKind.value === 'lost' && lostDetail.value) resetLostForm(lostDetail.value);
  if (dialogKind.value === 'found' && foundDetail.value) resetFoundForm(foundDetail.value);
  imageUploading.value = false;
  imageUploadError.value = null;
  editing.value = true;
  if (needsLegacyImageReplacement.value) {
    ElMessage.warning('旧记录缺少可提交的图片引用；保存前请重新上传图片，避免覆盖清空');
  }
}

function cancelEdit() {
  if (dialogKind.value === 'lost' && lostDetail.value) resetLostForm(lostDetail.value);
  if (dialogKind.value === 'found' && foundDetail.value) resetFoundForm(foundDetail.value);
  editing.value = false;
}

async function saveEdit() {
  if (saving.value) return;
  if (imageUploading.value) {
    ElMessage.warning('图片仍在上传，请稍候');
    return;
  }
  if (imageUploadError.value) {
    ElMessage.warning('有图片上传失败，请移除后重试');
    return;
  }
  if (needsLegacyImageReplacement.value) {
    ElMessage.warning('旧图片不能安全沿用，请重新上传后再保存');
    return;
  }
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  saving.value = true;
  try {
    if (dialogKind.value === 'lost' && lostDetail.value) {
      const id = lostDetail.value.id;
      await updateLostItem(id, {
        itemName: lostForm.itemName,
        category: lostForm.category,
        description: lostForm.description || null,
        lostTimeStart: toBackendDateTime(lostForm.lostRange[0]),
        lostTimeEnd: toBackendDateTime(lostForm.lostRange[1]),
        lostLocation: lostForm.lostLocation,
        subscribeMatch: lostForm.subscribeMatch,
        imageUrls: lostForm.imageUrls,
      });
      const updated = await getLostItem(id);
      lostDetail.value = updated;
      resetLostForm(updated);
    }
    if (dialogKind.value === 'found' && foundDetail.value) {
      let verifyQuestions;
      if (foundQuestionMode.value === 'REPLACE') {
        const parsed = parseVerifyQuestionDrafts(foundQuestions.value);
        questionErrors.value = parsed.errors;
        if (!parsed.questions) {
          ElMessage.warning('请修正验证问题中的字段错误');
          return;
        }
        verifyQuestions = parsed.questions;
      }
      const id = foundDetail.value.id;
      await updateFoundItem(id, {
        itemName: foundForm.itemName,
        category: foundForm.category,
        description: foundForm.description || null,
        foundTime: toBackendDateTime(foundForm.foundTime),
        foundLocation: foundForm.foundLocation,
        custodyType: foundForm.custodyType,
        contactPreference: foundForm.contactPreference,
        imageUrls: foundForm.imageUrls,
        ...(verifyQuestions !== undefined ? { verifyQuestions } : {}),
      });
      const updated = await getFoundItem(id);
      foundDetail.value = updated;
      resetFoundForm(updated);
    }
    editing.value = false;
    ElMessage.success('已保存');
    await loadKind(dialogKind.value);
  } catch (err) {
    if (isConflictApiError(err)) {
      editing.value = false;
      ElMessage.warning('物品状态已变化，已退出旧操作并刷新最新数据');
      await Promise.all([openCard(
        dialogKind.value === 'lost' ? lostDetail.value!.id : foundDetail.value!.id,
        dialogKind.value,
      ), loadKind(dialogKind.value)]);
      return;
    }
    ElMessage.error(err instanceof ApiError ? err.message : '保存失败');
  } finally {
    saving.value = false;
  }
}

async function updateStatus(status: 'FOUND' | 'CLOSED') {
  const isLost = dialogKind.value === 'lost';
  const id = isLost ? lostDetail.value?.id : foundDetail.value?.id;
  if (!id) return;
  const label = status === 'FOUND' ? '标记已找回' : '关闭';
  try {
    await ElMessageBox.confirm(`确认${label}这条发布吗？`, label, { type: 'warning' });
  } catch {
    return;
  }
  changingStatus.value = true;
  try {
    if (isLost) {
      await changeLostItemStatus(id, { status });
      lostDetail.value = await getLostItem(id);
      resetLostForm(lostDetail.value);
    } else {
      await changeFoundItemStatus(id, { status: 'CLOSED' });
      foundDetail.value = await getFoundItem(id);
      resetFoundForm(foundDetail.value);
    }
    ElMessage.success('状态已更新');
    await loadKind(dialogKind.value);
  } catch (err) {
    if (isConflictApiError(err)) {
      ElMessage.warning('物品状态已变化，已关闭旧操作并刷新最新数据');
      await Promise.all([openCard(id, dialogKind.value), loadKind(dialogKind.value)]);
      return;
    }
    ElMessage.error(err instanceof ApiError ? err.message : '状态更新失败');
  } finally {
    changingStatus.value = false;
  }
}

function goMatches() {
  const detail = dialogKind.value === 'lost' ? lostDetail.value : foundDetail.value;
  if (!detail) return;
  void router.push({
    name: 'matches',
    query: { bizType: dialogKind.value === 'lost' ? 'LOST' : 'FOUND', bizId: detail.id },
  });
}

const detailImages = computed(() => {
  if (dialogKind.value === 'lost') return lostDetail.value?.imageUrls ?? [];
  return foundDetail.value?.imageUrls ?? [];
});

function addFoundQuestion() {
  if (foundQuestions.value.length < 3) {
    foundQuestions.value.push({ questionText: '', answerKeywords: '' });
  }
}

function removeFoundQuestion(index: number) {
  foundQuestions.value.splice(index, 1);
  if (!foundQuestions.value.length) {
    foundQuestions.value.push({ questionText: '', answerKeywords: '' });
  }
  questionErrors.value = {};
}

watch(
  () => route.fullPath,
  () => {
    const state = parseMyItemsQuery(route.query);
    const pageChanged = state.tab === 'lost'
      ? lostPage.value !== state.page
      : foundPage.value !== state.page;
    tab.value = state.tab;
    if (state.tab === 'lost') lostPage.value = state.page;
    else foundPage.value = state.page;
    if (pageChanged) void loadKind(state.tab);
    if (state.targetId) void openCard(state.targetId, state.tab);
  },
);

onMounted(async () => {
  const canonical = {
    name: 'my-items',
    query: buildMyItemsQuery(initialQuery.tab, initialQuery.page, initialQuery.targetId),
  };
  if (router.resolve(canonical).fullPath !== route.fullPath) {
    await router.replace(canonical);
  }
  await Promise.all([loadKind('lost'), loadKind('found')]);
  if (initialQuery.targetId && !dialogVisible.value) {
    await openCard(initialQuery.targetId, initialQuery.tab);
  }
});
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="My posts"
      title="我的发布"
      description="管理失物和招领记录，查看匹配结果，完成关闭或找回状态流转。"
      back-fallback="/profile"
    />

    <el-radio-group v-model="tab" size="large" @change="changeTab">
      <el-radio-button label="lost">失物 ({{ lostTotal }})</el-radio-button>
      <el-radio-button label="found">招领 ({{ foundTotal }})</el-radio-button>
    </el-radio-group>

    <el-skeleton v-if="visibleLoading && !visibleList.length" :rows="4" animated />
    <template v-else>
      <EmptyState
        v-if="visibleError && !visibleList.length"
        title="我的发布加载失败"
        :description="visibleError"
        action-text="重试"
        @action="loadKind(tab)"
      />
      <el-alert
        v-else-if="visibleError"
        type="warning"
        :closable="false"
        :title="`${visibleError}，当前保留上次成功结果`"
      >
        <template #default><el-button link type="primary" @click="loadKind(tab)">重试</el-button></template>
      </el-alert>
      <div v-if="visibleList.length" v-loading="visibleLoading" class="grid">
        <ItemCard
          v-for="item in visibleList"
          :key="item.id"
          :kind="tab === 'lost' ? 'lost' : 'found'"
          :item="item"
          show-review
          @open="(id) => openFromCard(id, tab)"
        />
      </div>
      <EmptyState
        v-else-if="!visibleError"
        :title="tab === 'lost' ? '还没有发布过失物' : '还没有发布过招领'"
        action-text="去发布"
        @action="router.push(tab === 'lost' ? '/publish/lost' : '/publish/found')"
      />
      <el-pagination
        v-if="visibleTotal > pageSize"
        :current-page="visiblePage"
        :page-size="pageSize"
        :total="visibleTotal"
        layout="prev, pager, next"
        background
        class="pagination"
        @current-change="changePage"
      />
    </template>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogKind === 'lost' ? '失物详情' : '招领详情'"
      :width="dialogWidth"
      :top="isMobile ? '6vh' : '15vh'"
      class="detail-dialog"
      :close-on-click-modal="false"
      destroy-on-close
      @closed="closeDetailRoute"
    >
      <el-skeleton v-if="dialogLoading" :rows="6" animated />

      <template v-else-if="dialogKind === 'lost' && lostDetail">
        <div v-if="!editing" class="detail">
          <div class="badges">
            <el-tag round effect="dark">{{ categoryLabels[lostDetail.category] }}</el-tag>
            <StatusTag variant="lost" :value="lostDetail.status" />
            <StatusTag variant="review" :value="lostDetail.reviewStatus" />
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
            <el-descriptions-item label="订阅匹配">{{ lostDetail.subscribeMatch ? '已订阅' : '未订阅' }}</el-descriptions-item>
            <el-descriptions-item label="匹配数">{{ lostDetail.matchCount ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="发布时间">{{ shortDateTime(lostDetail.createdAt) }}</el-descriptions-item>
            <el-descriptions-item label="审核状态">
              <StatusTag variant="review" :value="lostDetail.reviewStatus" />
            </el-descriptions-item>
            <el-descriptions-item label="审核意见">{{ lostDetail.reviewComment || '暂无' }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <el-form v-else ref="formRef" :model="lostForm" :rules="lostRules" label-position="top">
          <el-form-item label="物品名称" prop="itemName">
            <el-input v-model="lostForm.itemName" maxlength="100" />
          </el-form-item>
          <el-form-item label="物品类别" prop="category">
            <el-select v-model="lostForm.category" style="width: 100%">
              <el-option v-for="opt in categoryOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="丢失时间区间" prop="lostRange">
            <el-date-picker
              v-model="lostForm.lostRange"
              type="datetimerange"
              range-separator="至"
              start-placeholder="开始时间"
              end-placeholder="结束时间"
              format="YYYY-MM-DD HH:mm"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="丢失地点" prop="lostLocation">
            <el-input v-model="lostForm.lostLocation" maxlength="100" />
          </el-form-item>
          <el-form-item label="物品描述" prop="description">
            <el-input v-model="lostForm.description" type="textarea" :rows="4" maxlength="500" show-word-limit />
          </el-form-item>
          <el-form-item label="物品图片">
            <el-alert
              v-if="hasLegacyLostImages"
              class="legacy-alert"
              type="warning"
              :closable="false"
              title="旧记录缺少可复用图片引用，保存前必须重新上传图片；系统不会静默清空原图。"
            />
            <ImageUploader
              v-model="lostForm.imageUrls"
              :preview-urls="lostDetail.imageUrls"
              biz-type="LOST"
              :max="5"
              @uploading-change="imageUploading = $event"
              @error-change="imageUploadError = $event"
            />
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="lostForm.subscribeMatch">订阅匹配提醒</el-checkbox>
          </el-form-item>
        </el-form>
      </template>

      <template v-else-if="dialogKind === 'found' && foundDetail">
        <div v-if="!editing" class="detail">
          <div class="badges">
            <el-tag round effect="dark">{{ categoryLabels[foundDetail.category] }}</el-tag>
            <StatusTag variant="found" :value="foundDetail.status" />
            <StatusTag variant="review" :value="foundDetail.reviewStatus" />
          </div>
          <h3 class="title">{{ foundDetail.itemName }}</h3>
          <p class="desc">{{ foundDetail.description || '发布者未填写描述' }}</p>
          <div v-if="!foundDetail.isSensitive && detailImages.length" class="thumbs">
            <img v-for="img in detailImages" :key="img" :src="img" :alt="foundDetail.itemName" />
          </div>
          <el-alert v-else-if="foundDetail.isSensitive" type="warning" :closable="false" title="敏感物品，图片已脱敏" />
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="拾获时间">{{ shortDateTime(foundDetail.foundTime) }}</el-descriptions-item>
            <el-descriptions-item label="拾获地点">{{ foundDetail.foundLocation }}</el-descriptions-item>
            <el-descriptions-item label="保管方式">{{ custodyTypeLabels[foundDetail.custodyType] }}</el-descriptions-item>
            <el-descriptions-item label="联系偏好">{{ contactPreferenceLabels[foundDetail.contactPreference] }}</el-descriptions-item>
            <el-descriptions-item label="发布时间">{{ shortDateTime(foundDetail.createdAt) }}</el-descriptions-item>
            <el-descriptions-item label="审核状态">
              <StatusTag variant="review" :value="foundDetail.reviewStatus" />
            </el-descriptions-item>
            <el-descriptions-item label="审核意见">{{ foundDetail.reviewComment || '暂无' }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <el-form v-else ref="formRef" :model="foundForm" :rules="foundRules" label-position="top">
          <el-form-item label="物品名称" prop="itemName">
            <el-input v-model="foundForm.itemName" maxlength="100" />
          </el-form-item>
          <el-form-item label="物品类别" prop="category">
            <el-select v-model="foundForm.category" style="width: 100%">
              <el-option v-for="opt in categoryOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="拾获时间" prop="foundTime">
            <el-date-picker v-model="foundForm.foundTime" type="datetime" format="YYYY-MM-DD HH:mm" style="width: 100%" />
          </el-form-item>
          <el-form-item label="拾获地点" prop="foundLocation">
            <el-input v-model="foundForm.foundLocation" maxlength="100" />
          </el-form-item>
          <el-form-item label="保管方式" prop="custodyType">
            <el-select v-model="foundForm.custodyType" style="width: 100%">
              <el-option v-for="opt in custodyOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="联系偏好" prop="contactPreference">
            <el-select v-model="foundForm.contactPreference" style="width: 100%">
              <el-option v-for="opt in contactOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="公开描述" prop="description">
            <el-input v-model="foundForm.description" type="textarea" :rows="4" maxlength="500" show-word-limit />
          </el-form-item>
          <el-form-item label="物品图片">
            <el-alert
              v-if="hasLegacyFoundImages"
              class="legacy-alert"
              type="warning"
              :closable="false"
              title="旧记录缺少可复用图片引用，保存前必须重新上传图片；系统不会静默清空原图。"
            />
            <ImageUploader
              v-model="foundForm.imageUrls"
              :preview-urls="foundDetail.imageUrls"
              biz-type="FOUND"
              :max="5"
              @uploading-change="imageUploading = $event"
              @error-change="imageUploadError = $event"
            />
          </el-form-item>
          <el-form-item label="验证问题">
            <el-radio-group v-model="foundQuestionMode">
              <el-radio-button label="KEEP">保留现有问题</el-radio-button>
              <el-radio-button label="REPLACE">替换现有问题</el-radio-button>
            </el-radio-group>
            <p class="form-tip">
              {{ foundQuestionMode === 'KEEP'
                ? `将保留当前 ${foundDetail.verifyQuestions.length} 个验证问题，不提交覆盖字段。`
                : '新问题将整体替换现有问题；整行留空表示不设置验证问题。' }}
            </p>
          </el-form-item>
          <div v-if="foundQuestionMode === 'REPLACE'" class="question-editor">
            <div v-for="(question, index) in foundQuestions" :key="index" class="question-row">
              <div class="question-field">
                <el-input v-model="question.questionText" maxlength="100" placeholder="验证问题" />
                <span v-if="questionErrors[index]?.questionText" class="field-error">
                  {{ questionErrors[index].questionText }}
                </span>
              </div>
              <div class="question-field">
                <el-input v-model="question.answerKeywords" placeholder="答案关键词，逗号分隔" />
                <span v-if="questionErrors[index]?.answerKeywords" class="field-error">
                  {{ questionErrors[index].answerKeywords }}
                </span>
              </div>
              <el-button type="danger" link @click="removeFoundQuestion(index)">删除</el-button>
            </div>
            <el-button link type="primary" :disabled="foundQuestions.length >= 3" @click="addFoundQuestion">
              新增问题
            </el-button>
          </div>
        </el-form>
      </template>

      <template #footer>
        <template v-if="!editing && (lostDetail || foundDetail)">
          <el-button @click="goMatches">查看匹配</el-button>
          <el-button
            v-if="dialogKind === 'lost'"
            type="success"
            plain
            :loading="changingStatus"
            :disabled="lostDetail?.status !== 'SEARCHING'"
            @click="updateStatus('FOUND')"
          >
            标记已找回
          </el-button>
          <el-button
            type="warning"
            plain
            :loading="changingStatus"
            :disabled="dialogKind === 'lost' ? lostDetail?.status !== 'SEARCHING' : !canCloseFound"
            @click="updateStatus('CLOSED')"
          >
            关闭
          </el-button>
          <el-button type="primary" @click="startEdit">编辑</el-button>
          <el-button @click="dialogVisible = false">返回</el-button>
        </template>
        <template v-else-if="editing">
          <el-button @click="cancelEdit">取消</el-button>
          <el-button
            type="primary"
            :loading="saving"
            :disabled="imageUploading || Boolean(imageUploadError) || needsLegacyImageReplacement"
            @click="saveEdit"
          >保存</el-button>
        </template>
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

.pagination {
  justify-content: center;
}

.legacy-alert {
  margin-bottom: 10px;
}

.form-tip {
  width: 100%;
  margin: 6px 0 0;
  color: var(--xunji-text-muted);
  font-size: 12px;
}

.question-editor,
.question-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.question-editor {
  margin-bottom: 18px;
}

.question-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  align-items: start;
  gap: 8px;
}

.field-error {
  color: var(--el-color-danger);
  font-size: 12px;
}

.detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
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
  }
  .desc {
    margin: 0;
    color: var(--xunji-text-muted);
    font-size: 14px;
    line-height: 1.6;
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

@media (max-width: 720px) {
  .question-row {
    grid-template-columns: 1fr;
  }
}
</style>

<style lang="scss">
.detail-dialog {
  .el-dialog__body {
    max-height: 70vh;
    overflow-y: auto;
    overflow-x: hidden;
    padding-top: 12px;
  }

  .el-descriptions__cell,
  .el-descriptions__label,
  .el-descriptions__content {
    word-break: break-word;
  }

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
}

@media (max-width: 720px) {
  .detail-dialog {
    .el-dialog__body {
      padding-left: 16px;
      padding-right: 16px;
    }
    .el-dialog__footer {
      display: flex;
      flex-direction: column-reverse;
      gap: 8px;
      .el-button {
        width: 100%;
        margin-left: 0 !important;
      }
    }
  }
}
</style>
