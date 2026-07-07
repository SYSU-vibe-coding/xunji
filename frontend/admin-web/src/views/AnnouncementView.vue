<script setup lang="ts">
import { reactive, ref } from 'vue';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';

import { createAnnouncement } from '@/api/admin';
import { ApiError } from '@/api/http';
import { announcementStatusLabels } from '@xunji/shared';

const formRef = ref<FormInstance>();
const form = reactive({
  title: '',
  content: '',
  publishNow: true,
});
const submitting = ref(false);
const lastResult = ref<{ id: string; status: string } | null>(null);

const rules: FormRules = {
  title: [
    { required: true, message: '请输入公告标题' },
    { max: 100, message: '标题不超过 100 字' },
  ],
  content: [
    { required: true, message: '请输入公告内容' },
    { max: 5000, message: '内容不超过 5000 字' },
  ],
};

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  submitting.value = true;
  try {
    const result = await createAnnouncement({
      title: form.title.trim(),
      content: form.content,
      publishNow: form.publishNow,
    });
    lastResult.value = result;
    ElMessage.success(form.publishNow ? '公告已发布' : '草稿已保存');
    form.title = '';
    form.content = '';
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="form-card">
      <template #header>
        <strong>发布公告</strong>
      </template>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="公告标题" prop="title">
          <el-input v-model="form.title" maxlength="100" show-word-limit placeholder="如：本周长期未领物品清单" />
        </el-form-item>
        <el-form-item label="公告内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="10"
            maxlength="5000"
            show-word-limit
            placeholder="支持普通文本，建议附上时间、地点、联系方式"
          />
        </el-form-item>
        <el-form-item>
          <el-switch
            v-model="form.publishNow"
            active-text="立即发布"
            inactive-text="保存为草稿"
          />
        </el-form-item>

        <el-button type="primary" size="large" :loading="submitting" @click="submit">
          {{ form.publishNow ? '发布公告' : '保存草稿' }}
        </el-button>
      </el-form>
    </el-card>

    <el-alert
      v-if="lastResult"
      type="success"
      :closable="false"
      :title="`最近一次提交：${lastResult.id} · ${announcementStatusLabels[lastResult.status as keyof typeof announcementStatusLabels] ?? lastResult.status}`"
    />
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 880px;
}
.form-card :deep(.el-card__header) {
  padding: 14px 18px;
  font-size: 15px;
}
</style>
