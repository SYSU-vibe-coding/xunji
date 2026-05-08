<script setup lang="ts">
import { computed } from 'vue';
import {
  ElMessage,
  type UploadProps,
  type UploadRawFile,
  type UploadRequestOptions,
  type UploadUserFile,
} from 'element-plus';
import { Plus } from '@element-plus/icons-vue';
import type { BizType } from '@xunji/shared';

import { uploadFile } from '@/api/upload';
import { ApiError } from '@/api/http';

const props = withDefaults(
  defineProps<{
    modelValue: string[];
    bizType: BizType;
    max?: number;
    accept?: string;
    sizeLimitMb?: number;
  }>(),
  { max: 5, accept: 'image/*', sizeLimitMb: 10 },
);

const emit = defineEmits<{ 'update:modelValue': [urls: string[]] }>();

const fileList = computed<UploadUserFile[]>(() =>
  props.modelValue.map((url, idx) => ({ name: `图片 ${idx + 1}`, url, status: 'success' })),
);

const beforeUpload: UploadProps['beforeUpload'] = (raw: UploadRawFile) => {
  if (raw.size > props.sizeLimitMb * 1024 * 1024) {
    ElMessage.warning(`图片大小不能超过 ${props.sizeLimitMb}MB`);
    return false;
  }
  return true;
};

async function customRequest(options: UploadRequestOptions) {
  try {
    const result = await uploadFile(options.file as File, props.bizType);
    emit('update:modelValue', [...props.modelValue, result.url]);
    options.onSuccess(result);
  } catch (err) {
    const msg = err instanceof ApiError ? err.message : '上传失败';
    ElMessage.error(msg);
    const uploadError = Object.assign(err instanceof Error ? err : new Error(msg), {
      name: 'UploadAjaxError',
      status: 0,
      method: options.method,
      url: options.action,
    });
    options.onError(uploadError);
  }
}

function handleRemove(file: UploadUserFile) {
  const next = props.modelValue.filter((url) => url !== file.url);
  emit('update:modelValue', next);
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
