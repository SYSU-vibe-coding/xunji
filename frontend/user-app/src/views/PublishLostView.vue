<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, type FormInstance, type FormItemRule, type FormRules } from 'element-plus';

import ImageUploader from '@/components/ImageUploader.vue';
import PageHeader from '@/components/PageHeader.vue';
import { createLostItem } from '@/api/item';
import { ApiError } from '@/api/http';
import { categoryOptions, type ItemCategory } from '@xunji/shared';
import { toBackendDateTime } from '@/utils/format';

const router = useRouter();
const formRef = ref<FormInstance>();

const form = reactive({
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
  description: [{ max: 500, message: '描述不超过 500 字' }],
};

const submitting = ref(false);

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  submitting.value = true;
  try {
    const result = await createLostItem({
      itemName: form.itemName,
      category: form.category,
      description: form.description || null,
      lostTimeStart: toBackendDateTime(form.lostRange[0]),
      lostTimeEnd: toBackendDateTime(form.lostRange[1]),
      lostLocation: form.lostLocation,
      subscribeMatch: form.subscribeMatch,
      imageUrls: form.imageUrls,
    });
    ElMessage.success('失物发布成功');
    void router.push(`/items/lost/${result.id}`);
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '发布失败');
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Publish · Lost"
      title="发布失物信息"
      description="提交后系统会自动匹配相似招领，并通过站内消息提醒"
      back-fallback="/"
    />

    <el-card shadow="never">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="form"
      >
        <div class="grid">
          <el-form-item label="物品名称" prop="itemName">
            <el-input v-model="form.itemName" maxlength="100" placeholder="如：白色 AirPods Pro" />
          </el-form-item>
          <el-form-item label="物品类别" prop="category">
            <el-select v-model="form.category" placeholder="请选择类别" style="width: 100%">
              <el-option
                v-for="opt in categoryOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="丢失时间区间" prop="lostRange" class="span-2">
            <el-date-picker
              v-model="form.lostRange"
              type="datetimerange"
              range-separator="至"
              start-placeholder="开始时间"
              end-placeholder="结束时间"
              format="YYYY-MM-DD HH:mm"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="丢失地点" prop="lostLocation" class="span-2">
            <el-input v-model="form.lostLocation" maxlength="100" placeholder="如：图书馆二楼东侧自习区" />
          </el-form-item>
          <el-form-item label="物品描述" prop="description" class="span-2">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="4"
              maxlength="500"
              show-word-limit
              placeholder="颜色、品牌、特殊标记等关键信息"
            />
          </el-form-item>
          <el-form-item label="物品图片（最多 5 张）" class="span-2">
            <ImageUploader v-model="form.imageUrls" biz-type="LOST" :max="5" />
          </el-form-item>
          <el-form-item class="span-2">
            <el-checkbox v-model="form.subscribeMatch">
              订阅匹配提醒，发现相似招领自动通知
            </el-checkbox>
          </el-form-item>
        </div>

        <div class="footer-actions">
          <el-button @click="router.push('/')">取消</el-button>
          <el-button type="primary" size="large" :loading="submitting" @click="submit">
            发布失物
          </el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
  max-width: 880px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0 18px;

  .span-2 {
    grid-column: span 2;
  }
}

.footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--xunji-border);
}

@media (max-width: 720px) {
  .grid {
    grid-template-columns: 1fr;
    .span-2 {
      grid-column: span 1;
    }
  }
  .footer-actions {
    flex-direction: column-reverse;
    align-items: stretch;
    .el-button {
      width: 100%;
      margin-left: 0 !important;
    }
  }
}
</style>
