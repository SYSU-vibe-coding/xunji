<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';

import StatusTag from '@/components/StatusTag.vue';
import { handleReport, listReports } from '@/api/admin';
import { ApiError } from '@/api/http';
import {
  type ReportRecord,
  reportTargetTypeLabels,
} from '@xunji/shared';
import { shortDateTime } from '@/utils/format';

const list = ref<ReportRecord[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 10;
const loading = ref(true);

const dialogVisible = ref(false);
const dialogRecord = ref<ReportRecord | null>(null);
const dialogForm = reactive<{ action: 'VALID' | 'INVALID'; result: string; creditDelta: number }>({
  action: 'VALID',
  result: '',
  creditDelta: -10,
});
const submitting = ref(false);

async function load() {
  loading.value = true;
  try {
    const data = await listReports({ pageNo: page.value, pageSize });
    list.value = data.list;
    total.value = data.total;
  } catch (err) {
    if (err instanceof ApiError && err.code === 40002) return;
    list.value = [];
  } finally {
    loading.value = false;
  }
}

function openDialog(record: ReportRecord) {
  dialogRecord.value = record;
  dialogForm.action = 'VALID';
  dialogForm.result = '举报有效，已扣减信用分并通知双方';
  dialogForm.creditDelta = -10;
  dialogVisible.value = true;
}

async function submit() {
  if (!dialogRecord.value) return;
  if (!dialogForm.result.trim()) {
    ElMessage.warning('请输入处理结果');
    return;
  }
  submitting.value = true;
  try {
    await handleReport(dialogRecord.value.id, {
      action: dialogForm.action,
      result: dialogForm.result.trim(),
      ...(dialogForm.action === 'VALID'
        ? { creditDelta: dialogForm.creditDelta, reasonCode: 'FRAUD_CLAIM_CONFIRMED' }
        : {}),
    });
    ElMessage.success('已处理');
    dialogVisible.value = false;
    await load();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '操作失败');
  } finally {
    submitting.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="page">
    <el-card shadow="never">
      <el-table v-loading="loading" :data="list" stripe border style="width: 100%">
        <el-table-column prop="reason" label="举报原因" min-width="180" />
        <el-table-column label="目标类型" width="120">
          <template #default="{ row }">{{ reportTargetTypeLabels[row.targetType as keyof typeof reportTargetTypeLabels] }}</template>
        </el-table-column>
        <el-table-column prop="targetId" label="目标 ID" min-width="240" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <StatusTag variant="report" :value="row.handleStatus" />
          </template>
        </el-table-column>
        <el-table-column label="举报时间" width="160">
          <template #default="{ row }">{{ shortDateTime(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              :disabled="row.handleStatus !== 'PENDING' && row.handleStatus !== 'PROCESSING'"
              @click="openDialog(row)"
            >
              处理
            </el-button>
          </template>
        </el-table-column>
      </el-table>

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

    <el-dialog v-model="dialogVisible" title="处理举报" width="520px">
      <el-form label-position="top">
        <el-form-item label="举报原因">
          <el-input :model-value="dialogRecord?.reason" disabled />
        </el-form-item>
        <el-form-item label="处理结论">
          <el-radio-group v-model="dialogForm.action">
            <el-radio-button label="VALID">举报有效</el-radio-button>
            <el-radio-button label="INVALID">举报无效</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="处理说明">
          <el-input
            v-model="dialogForm.result"
            type="textarea"
            :rows="3"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
        <el-form-item v-if="dialogForm.action === 'VALID'" label="信誉分变动（被举报人）">
          <el-input-number v-model="dialogForm.creditDelta" :min="-50" :max="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">确认处理</el-button>
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
.pagination {
  margin-top: 14px;
  justify-content: center;
}
</style>
