<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';

import {
  createAnnouncement,
  listAnnouncements,
  offlineAnnouncement,
  publishAnnouncement,
} from '@/api/admin';
import { ApiError, isUnauthorizedApiError } from '@/api/http';
import { lastPage } from '@/utils/admin-list';
import { shortDateTime } from '@/utils/format';
import {
  type AnnouncementRecord,
  type AnnouncementStatus,
  announcementStatusLabels,
} from '@xunji/shared';

const list = ref<AnnouncementRecord[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 10;
const status = ref<AnnouncementStatus | ''>('');
const loading = ref(true);
const errorMessage = ref('');
const actionLoadingId = ref('');

const editorVisible = ref(false);
const formRef = ref<FormInstance>();
const form = reactive({ title: '', content: '' });
const submitting = ref<'draft' | 'publish' | ''>('');
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

async function load() {
  loading.value = true;
  errorMessage.value = '';
  try {
    const data = await listAnnouncements({
      status: status.value || undefined,
      pageNo: page.value,
      pageSize,
    });
    const finalPage = lastPage(data.total, pageSize);
    if (page.value > finalPage) {
      page.value = finalPage;
      await load();
      return;
    }
    list.value = data.list;
    total.value = data.total;
  } catch (err) {
    if (isUnauthorizedApiError(err)) return;
    list.value = [];
    total.value = 0;
    errorMessage.value = err instanceof ApiError ? err.message : '公告列表加载失败';
  } finally {
    loading.value = false;
  }
}

function filter() {
  page.value = 1;
  void load();
}

function openEditor() {
  form.title = '';
  form.content = '';
  editorVisible.value = true;
}

async function submit(publishNow: boolean) {
  if (submitting.value) return;
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  if (publishNow) {
    try {
      await ElMessageBox.confirm(
        '立即发布后，所有启用用户将收到可直达公告详情的系统通知。',
        '确认发布公告',
        { type: 'warning', confirmButtonText: '确认发布', cancelButtonText: '取消' },
      );
    } catch {
      return;
    }
  }
  submitting.value = publishNow ? 'publish' : 'draft';
  try {
    await createAnnouncement({
      title: form.title.trim(),
      content: form.content.trim(),
      publishNow,
    });
    ElMessage.success(publishNow ? '公告已发布并通知用户' : '公告草稿已保存');
    editorVisible.value = false;
    page.value = 1;
    await load();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  } finally {
    submitting.value = '';
  }
}

async function publish(record: AnnouncementRecord) {
  if (actionLoadingId.value === record.id) return;
  actionLoadingId.value = record.id;
  try {
    await ElMessageBox.confirm(
      `确认发布“${record.title}”？发布后将通知所有启用用户。`,
      '发布公告',
      { type: 'warning', confirmButtonText: '确认发布', cancelButtonText: '取消' },
    );
    await publishAnnouncement(record.id);
    ElMessage.success('公告已发布');
    await load();
  } catch (err) {
    if (err === 'cancel' || err === 'close') return;
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
    await load();
  } finally {
    actionLoadingId.value = '';
  }
}

async function takeOffline(record: AnnouncementRecord) {
  if (actionLoadingId.value === record.id) return;
  actionLoadingId.value = record.id;
  try {
    await ElMessageBox.confirm(
      `确认下线“${record.title}”？下线后用户列表和通知深链均不可再访问。`,
      '下线公告',
      { type: 'warning', confirmButtonText: '确认下线', cancelButtonText: '取消' },
    );
    await offlineAnnouncement(record.id);
    ElMessage.success('公告已下线');
    await load();
  } catch (err) {
    if (err === 'cancel' || err === 'close') return;
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
    await load();
  } finally {
    actionLoadingId.value = '';
  }
}

onMounted(load);
</script>

<template>
  <div class="page">
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <el-radio-group v-model="status" @change="filter">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button
            v-for="(label, value) in announcementStatusLabels"
            :key="value"
            :label="value"
          >
            {{ label }}
          </el-radio-button>
        </el-radio-group>
        <el-button type="primary" @click="openEditor">新建公告</el-button>
      </div>
    </el-card>

    <el-card shadow="never">
      <el-result v-if="errorMessage" icon="error" title="公告列表加载失败" :sub-title="errorMessage">
        <template #extra><el-button type="primary" @click="load">重试</el-button></template>
      </el-result>
      <el-table v-else-if="loading || list.length" v-loading="loading" :data="list" stripe border>
        <el-table-column label="公告" min-width="260">
          <template #default="{ row }">
            <strong>{{ row.title }}</strong>
            <p class="content-preview">{{ row.content }}</p>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'PUBLISHED' ? 'success' : row.status === 'DRAFT' ? 'warning' : 'info'"
              effect="light"
              round
            >
              {{ announcementStatusLabels[row.status as AnnouncementStatus] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ shortDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="发布时间" width="170">
          <template #default="{ row }">{{ row.publishedAt ? shortDateTime(row.publishedAt) : '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'DRAFT'"
              type="primary"
              size="small"
              :loading="actionLoadingId === row.id"
              @click="publish(row)"
            >
              发布
            </el-button>
            <el-button
              v-else-if="row.status === 'PUBLISHED'"
              type="danger"
              plain
              size="small"
              :loading="actionLoadingId === row.id"
              @click="takeOffline(row)"
            >
              下线
            </el-button>
            <span v-else class="muted">已归档</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="当前筛选条件下没有公告" />

      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        background
        class="pagination"
        @current-change="load"
      />
    </el-card>

    <el-drawer
      v-model="editorVisible"
      title="新建公告"
      size="min(620px, 94vw)"
      :close-on-click-modal="!submitting"
      :close-on-press-escape="!submitting"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="公告标题" prop="title">
          <el-input v-model="form.title" maxlength="100" show-word-limit placeholder="输入清晰、可检索的公告标题" />
        </el-form-item>
        <el-form-item label="公告内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="13"
            maxlength="5000"
            show-word-limit
            placeholder="说明时间、影响范围及用户需要采取的行动"
          />
        </el-form-item>
        <el-alert
          type="info"
          show-icon
          :closable="false"
          title="发布闭环"
          description="保存草稿后可从列表发布；立即发布会同步生成系统通知，通知点击后准确打开该公告。"
        />
      </el-form>
      <template #footer>
        <el-button :loading="submitting === 'draft'" :disabled="Boolean(submitting)" @click="submit(false)">
          保存草稿
        </el-button>
        <el-button
          type="primary"
          :loading="submitting === 'publish'"
          :disabled="Boolean(submitting)"
          @click="submit(true)"
        >
          立即发布
        </el-button>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.toolbar-card :deep(.el-card__body) {
  padding: 14px 16px;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.content-preview {
  max-width: 680px;
  margin: 5px 0 0;
  overflow: hidden;
  color: var(--xunji-text-muted);
  font-size: 13px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.muted {
  color: var(--xunji-text-muted);
  font-size: 12px;
}
.pagination {
  margin-top: 14px;
  justify-content: center;
}
</style>
