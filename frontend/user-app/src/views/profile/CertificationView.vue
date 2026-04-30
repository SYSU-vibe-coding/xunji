<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';

import ImageUploader from '@/components/ImageUploader.vue';
import PageHeader from '@/components/PageHeader.vue';
import StatusTag from '@/components/StatusTag.vue';
import { getMyCertification, submitCertification } from '@/api/user';
import { ApiError } from '@/api/http';
import { useAuthStore } from '@/stores/auth';
import type { CertificationDetail } from '@xunji/shared';
import { shortDateTime } from '@/utils/format';

const auth = useAuthStore();

const current = ref<CertificationDetail | null>(null);
const loading = ref(true);
const submitting = ref(false);

const form = reactive({
  campusId: '',
  realName: '',
  imageUrls: [] as string[],
});

async function load() {
  loading.value = true;
  try {
    const data = await getMyCertification();
    current.value = data;
    if (data) {
      form.campusId = data.campusId;
      form.realName = data.realName ?? '';
      form.imageUrls = data.documentImageUrl ? [data.documentImageUrl] : [];
    }
  } catch (err) {
    if (!(err instanceof ApiError && err.code === 40404)) {
      // 404 视为「尚未提交认证」，无需报错
    }
  } finally {
    loading.value = false;
  }
}

async function submit() {
  if (!form.campusId || !form.realName || !form.imageUrls.length) {
    ElMessage.warning('请填写完整信息并上传证件图片');
    return;
  }
  submitting.value = true;
  try {
    await submitCertification({
      campusId: form.campusId.trim(),
      realName: form.realName.trim(),
      documentImageUrl: form.imageUrls[0],
    });
    ElMessage.success('已提交，等待审核');
    await Promise.all([load(), auth.loadProfile()]);
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '提交失败');
  } finally {
    submitting.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Certification"
      title="实名认证"
      description="认证后可发布招领、参与高敏感物品认领"
      back-fallback="/profile"
    />

    <el-skeleton v-if="loading" :rows="4" animated />
    <template v-else>
      <el-card v-if="current" shadow="never" class="status-card">
        <div class="row">
          <strong>当前状态</strong>
          <StatusTag variant="review" :value="current.reviewStatus" />
        </div>
        <el-descriptions :column="1" border size="small" class="meta">
          <el-descriptions-item label="校园编号">{{ current.campusId }}</el-descriptions-item>
          <el-descriptions-item label="真实姓名">{{ current.realName ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ shortDateTime(current.createdAt) }}</el-descriptions-item>
          <el-descriptions-item v-if="current.reviewComment" label="审核意见">{{ current.reviewComment }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <strong>{{ current ? '重新提交' : '提交认证' }}</strong>
        </template>
        <el-form label-position="top">
          <el-form-item label="校园编号">
            <el-input v-model="form.campusId" maxlength="20" placeholder="学号 / 工号" />
          </el-form-item>
          <el-form-item label="真实姓名">
            <el-input v-model="form.realName" maxlength="20" placeholder="按证件填写" />
          </el-form-item>
          <el-form-item label="证件图片（仅 1 张）">
            <ImageUploader v-model="form.imageUrls" biz-type="CERT" :max="1" />
            <div class="tip">建议上传校园卡正面，确保信息清晰可读</div>
          </el-form-item>
        </el-form>
        <el-button type="primary" size="large" :loading="submitting" @click="submit">
          提交认证
        </el-button>
      </el-card>
    </template>
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
  max-width: 720px;
}
.status-card {
  .row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    strong {
      font-weight: 600;
    }
  }
}
.tip {
  margin-top: 6px;
  color: var(--xunji-text-muted);
  font-size: 12px;
}
</style>
