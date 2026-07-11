<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import {
  ElMessage,
  type UploadProps,
  type UploadRawFile,
  type UploadRequestOptions,
  type UploadUserFile,
} from 'element-plus';
import { Plus } from '@element-plus/icons-vue';
import type { UploadBizType } from '@xunji/shared';

import { uploadFile } from '@/api/upload';
import { ApiError } from '@/api/http';
import { appendUniqueUrl } from '@/utils/interaction';

const props = withDefaults(
  defineProps<{
    modelValue: string[];
    previewUrls?: string[];
    bizType: UploadBizType;
    max?: number;
    accept?: string;
    sizeLimitMb?: number;
  }>(),
  { max: 5, accept: 'image/*', sizeLimitMb: 10 },
);

const emit = defineEmits<{
  'update:modelValue': [urls: string[]];
  'uploading-change': [uploading: boolean];
  'error-change': [message: string | null];
}>();

const currentRefs = ref([...props.modelValue]);
const uploadedPreviews = ref<Record<string, string>>({});
const pendingUploads = ref(0);
const uploadErrors = new Map<number, string>();

watch(
  [() => props.modelValue, () => props.previewUrls],
  ([assetRefs, previewUrls]) => {
    currentRefs.value = [...assetRefs];
    assetRefs.forEach((assetRef, index) => {
      const previewUrl = previewUrls?.[index];
      if (previewUrl) uploadedPreviews.value[assetRef] = previewUrl;
    });
  },
  { deep: true, immediate: true },
);

function emitUploadError() {
  emit('error-change', uploadErrors.values().next().value ?? null);
}

function changePending(delta: number) {
  pendingUploads.value = Math.max(0, pendingUploads.value + delta);
  emit('uploading-change', pendingUploads.value > 0);
}

const fileList = computed<UploadUserFile[]>(() =>
  props.modelValue.map((assetRef, idx) => ({
    name: `图片 ${idx + 1}`,
    url: uploadedPreviews.value[assetRef],
    status: 'success',
  })),
);

const beforeUpload: UploadProps['beforeUpload'] = (raw: UploadRawFile) => {
  if (raw.size > props.sizeLimitMb * 1024 * 1024) {
    const message = `图片大小不能超过 ${props.sizeLimitMb}MB`;
    ElMessage.warning(message);
    return false;
  }
  return true;
};

async function customRequest(options: UploadRequestOptions) {
  uploadErrors.delete(options.file.uid);
  emitUploadError();
  changePending(1);
  try {
    const result = await uploadFile(options.file as File, props.bizType);
    uploadedPreviews.value[result.assetRef] = result.previewUrl;
    currentRefs.value = appendUniqueUrl(currentRefs.value, result.assetRef);
    emit('update:modelValue', currentRefs.value);
    options.onSuccess(result);
  } catch (err) {
    const msg = err instanceof ApiError ? err.message : '上传失败';
    uploadErrors.set(options.file.uid, msg);
    emitUploadError();
    ElMessage.error(msg);
    const uploadError = Object.assign(err instanceof Error ? err : new Error(msg), {
      name: 'UploadAjaxError',
      status: 0,
      method: options.method,
      url: options.action,
    });
    options.onError(uploadError);
  } finally {
    changePending(-1);
  }
}

function handleRemove(file: UploadUserFile) {
  const index = fileList.value.findIndex((candidate) => candidate.url === file.url);
  if (index >= 0) currentRefs.value.splice(index, 1);
  if (file.uid !== undefined) uploadErrors.delete(file.uid);
  emitUploadError();
  emit('update:modelValue', [...currentRefs.value]);
}

function onExceed() {
  ElMessage.warning(`最多上传 ${props.max} 张图片`);
}
</script>

<template>
  <el-upload
    :file-list="fileList"
    :limit="max"
    list-type="picture-card"
    :accept="accept"
    :before-upload="beforeUpload"
    :http-request="customRequest"
    :on-remove="handleRemove"
    :on-exceed="onExceed"
  >
    <el-icon><Plus /></el-icon>
  </el-upload>
</template>
