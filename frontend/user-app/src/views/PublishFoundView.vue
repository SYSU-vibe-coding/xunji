<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';
import { Delete, Plus } from '@element-plus/icons-vue';

import ImageUploader from '@/components/ImageUploader.vue';
import PageHeader from '@/components/PageHeader.vue';
import { createFoundItem } from '@/api/item';
import { ApiError } from '@/api/http';
import {
  categoryOptions,
  contactOptions,
  custodyOptions,
  type ContactPreference,
  type CustodyType,
  type ItemCategory,
} from '@xunji/shared';
import { toBackendDateTime } from '@/utils/format';
import {
  parseVerifyQuestionDrafts,
  type VerifyQuestionFieldErrors,
} from '@/utils/interaction';

interface QuestionRow {
  questionText: string;
  answerKeywords: string;
}

const router = useRouter();
const formRef = ref<FormInstance>();

const form = reactive({
  itemName: '',
  category: 'CERT' as ItemCategory,
  foundTime: null as Date | null,
  foundLocation: '',
  custodyType: 'SECURITY' as CustodyType,
  contactPreference: 'IN_APP' as ContactPreference,
  description: '',
  imageUrls: [] as string[],
  questions: [{ questionText: '', answerKeywords: '' }] as QuestionRow[],
});

const rules: FormRules = {
  itemName: [{ required: true, message: '请输入物品名称' }],
  category: [{ required: true, message: '请选择类别' }],
  foundTime: [{ required: true, message: '请选择拾获时间' }],
  foundLocation: [
    { required: true, message: '请输入拾获地点' },
    { max: 100, message: '地点不超过 100 字' },
  ],
  custodyType: [{ required: true, message: '请选择保管方式' }],
  contactPreference: [{ required: true, message: '请选择联系方式偏好' }],
  description: [{ max: 500, message: '描述不超过 500 字' }],
};

const submitting = ref(false);
const imageUploading = ref(false);
const imageUploadError = ref<string | null>(null);
const questionErrors = ref<Record<number, VerifyQuestionFieldErrors>>({});

function addQuestion() {
  if (form.questions.length >= 3) {
    ElMessage.warning('最多设置 3 个验证问题');
    return;
  }
  form.questions.push({ questionText: '', answerKeywords: '' });
  questionErrors.value = {};
}

function removeQuestion(idx: number) {
  form.questions.splice(idx, 1);
  questionErrors.value = {};
}

async function submit() {
  if (submitting.value) return;
  if (imageUploading.value) {
    ElMessage.warning('图片仍在上传，请稍候');
    return;
  }
  if (imageUploadError.value) {
    ElMessage.warning('有图片上传失败，请移除后重试');
    return;
  }
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  const parsedQuestions = parseVerifyQuestionDrafts(form.questions);
  questionErrors.value = parsedQuestions.errors;
  if (!parsedQuestions.questions) {
    ElMessage.warning('请修正验证问题中的字段错误');
    return;
  }

  submitting.value = true;
  try {
    const result = await createFoundItem({
      itemName: form.itemName,
      category: form.category,
      description: form.description || null,
      foundTime: toBackendDateTime(form.foundTime),
      foundLocation: form.foundLocation,
      custodyType: form.custodyType,
      contactPreference: form.contactPreference,
      imageUrls: form.imageUrls,
      verifyQuestions: parsedQuestions.questions,
    });
    ElMessage.success(result.isSensitive ? '招领发布成功（敏感物品已脱敏）' : '招领发布成功');
    void router.push(`/items/found/${result.id}`);
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
      eyebrow="Publish · Found"
      title="登记招领信息"
      description="填写验证问题可帮助你确认对方是真正的失主"
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
            <el-input v-model="form.itemName" maxlength="100" placeholder="如：校园一卡通" />
          </el-form-item>
          <el-form-item label="物品类别" prop="category">
            <el-select v-model="form.category" style="width: 100%">
              <el-option
                v-for="opt in categoryOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="拾获时间" prop="foundTime">
            <el-date-picker
              v-model="form.foundTime"
              type="datetime"
              placeholder="选择拾获时间"
              format="YYYY-MM-DD HH:mm"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="拾获地点" prop="foundLocation">
            <el-input v-model="form.foundLocation" maxlength="100" placeholder="如：南区食堂二楼" />
          </el-form-item>
          <el-form-item label="保管方式" prop="custodyType">
            <el-select v-model="form.custodyType" style="width: 100%">
              <el-option
                v-for="opt in custodyOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="联系方式偏好" prop="contactPreference">
            <el-select v-model="form.contactPreference" style="width: 100%">
              <el-option
                v-for="opt in contactOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="公开描述" prop="description" class="span-2">
            <el-input
              v-model="form.description"
              type="textarea"
              :rows="3"
              maxlength="500"
              show-word-limit
              placeholder="发现位置、可公开线索（不要写明显特征）"
            />
          </el-form-item>
          <el-form-item label="物品图片（最多 5 张）" class="span-2">
            <ImageUploader
              v-model="form.imageUrls"
              biz-type="FOUND"
              :max="5"
              @uploading-change="imageUploading = $event"
              @error-change="imageUploadError = $event"
            />
          </el-form-item>
        </div>

        <el-divider>验证问题（最多 3 个）</el-divider>

        <div v-for="(q, idx) in form.questions" :key="idx" class="question-row">
          <div class="question-field q-text">
            <el-input
              v-model="q.questionText"
              placeholder="如：请说出物品上的特殊标记"
              maxlength="100"
            />
            <span v-if="questionErrors[idx]?.questionText" class="field-error">
              {{ questionErrors[idx].questionText }}
            </span>
          </div>
          <div class="question-field q-ans">
            <el-input
              v-model="q.answerKeywords"
              placeholder="答案关键词，多个用逗号分隔"
            />
            <span v-if="questionErrors[idx]?.answerKeywords" class="field-error">
              {{ questionErrors[idx].answerKeywords }}
            </span>
          </div>
          <el-button
            type="danger"
            link
            :disabled="form.questions.length === 1"
            @click="removeQuestion(idx)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <el-button link type="primary" :disabled="form.questions.length >= 3" @click="addQuestion">
          <el-icon><Plus /></el-icon>新增验证问题
        </el-button>

        <div class="footer-actions">
          <el-button @click="router.push('/')">取消</el-button>
          <el-button
            type="primary"
            size="large"
            :loading="submitting"
            :disabled="imageUploading || Boolean(imageUploadError)"
            @click="submit"
          >
            发布招领
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

.question-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  margin-bottom: 10px;

  .q-text {
    flex: 1;
  }
  .q-ans {
    flex: 1;
  }
}

.question-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-error {
  color: var(--el-color-danger);
  font-size: 12px;
}

.footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 8px;
  margin-top: 8px;
  border-top: 1px solid var(--xunji-border);
}

@media (max-width: 720px) {
  .grid {
    grid-template-columns: 1fr;
    .span-2 {
      grid-column: span 1;
    }
  }
  .question-row {
    flex-wrap: wrap;
    .q-text,
    .q-ans {
      flex: 1 1 100%;
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
