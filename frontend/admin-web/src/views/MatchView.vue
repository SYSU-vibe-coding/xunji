<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Promotion, Refresh, Setting, Timer } from '@element-plus/icons-vue';

import { getMatchStatus, setMatchInterval, triggerMatchRun } from '@/api/admin';
import { ApiError, isUnauthorizedApiError } from '@/api/http';
import { shortDateTime } from '@/utils/format';
import { isConflictApiError, type MatchJobStatus } from '@xunji/shared';
import { createLatestRequestGuard } from '@/utils/admin-list';

const status = ref<MatchJobStatus | null>(null);
const loading = ref(true);
const errorMessage = ref('');
const intervalInput = ref(0);
const intervalSaving = ref(false);
const triggering = ref(false);
const now = ref(Date.now());
let timer: ReturnType<typeof setInterval> | null = null;
const requestGuard = createLatestRequestGuard();

const isRunning = computed(() => status.value?.status === 'running');
const progressPercent = computed(() => {
  const s = status.value;
  if (!s || s.totalPairs === 0) return 0;
  return Math.min(100, Math.round((s.processedPairs / s.totalPairs) * 100));
});

// 静默加载：只更新 status，不动 loading，避免骨架屏闪烁。
// intervalInput 只在首次加载或用户没在编辑/保存时同步，防止打断输入。
async function load(silent = false) {
  const requestId = requestGuard.next();
  if (!silent) loading.value = true;
  if (!silent) errorMessage.value = '';
  try {
    const s = await getMatchStatus();
    if (!requestGuard.isLatest(requestId)) return;
    status.value = s;
    if (!intervalSaving.value) {
      // 只在用户没有手动改过输入框时跟随服务器；用一个标记判断
      if (intervalTouched.value === false || s.intervalMinutes !== lastServerInterval.value) {
        intervalInput.value = s.intervalMinutes;
        lastServerInterval.value = s.intervalMinutes;
      }
    }
  } catch (err) {
    if (!requestGuard.isLatest(requestId) || isUnauthorizedApiError(err) || silent) return;
    status.value = null;
    errorMessage.value = err instanceof ApiError ? err.message : '加载匹配状态失败';
  } finally {
    if (!silent && requestGuard.isLatest(requestId)) loading.value = false;
  }
}

const intervalTouched = ref(false);
const lastServerInterval = ref(0);

async function triggerRun() {
  if (triggering.value || intervalSaving.value || isRunning.value) return;
  triggering.value = true;
  try {
    await ElMessageBox.confirm(
      '确认立即触发全量匹配？任务会对当前有效的失物和招领进行评分，并可能写入新的匹配结果。',
      '确认触发匹配',
      { type: 'warning', confirmButtonText: '确认触发', cancelButtonText: '取消' },
    );
    await triggerMatchRun();
    ElMessage.success('已触发匹配任务');
    await load(true);
  } catch (err) {
    if (err === 'cancel' || err === 'close') return;
    if (isConflictApiError(err)) {
      ElMessage.warning('匹配任务状态已变化，已刷新最新状态');
      await load(true);
      return;
    }
    if (!isUnauthorizedApiError(err)) {
      ElMessage.error('触发失败');
    }
  } finally {
    triggering.value = false;
  }
}

async function saveInterval() {
  if (intervalSaving.value || triggering.value) return;
  if (intervalInput.value < 0 || intervalInput.value > 1440) {
    ElMessage.warning('间隔范围 0-1440 分钟（0 表示关闭自动）');
    return;
  }
  try {
    await ElMessageBox.confirm(
      intervalInput.value === 0
        ? '确认关闭自动匹配？管理员仍可手动触发。'
        : `确认将自动匹配间隔设为 ${intervalInput.value} 分钟？`,
      '确认',
      { type: 'warning' },
    );
  } catch {
    return;
  }
  intervalSaving.value = true;
  try {
    await setMatchInterval({ intervalMinutes: intervalInput.value });
    ElMessage.success(intervalInput.value === 0 ? '已关闭自动匹配' : '已更新间隔');
    lastServerInterval.value = intervalInput.value;
    await load(true);
  } catch (err) {
    if (isConflictApiError(err)) {
      ElMessage.warning('匹配设置状态已变化，已刷新最新状态');
      await load(true);
      return;
    }
    if (!isUnauthorizedApiError(err)) {
      ElMessage.error('保存失败');
    }
  } finally {
    intervalSaving.value = false;
  }
}

function onIntervalInput(v: number | undefined) {
  intervalInput.value = v ?? 0;
  intervalTouched.value = true;
}

function statusTagType(s: string | undefined) {
  if (s === 'running') return 'warning';
  if (s === 'stopping') return 'info';
  return 'success';
}

function statusLabel(s: string | undefined) {
  if (s === 'running') return '运行中';
  if (s === 'stopping') return '停止中';
  return '空闲';
}

function nextRunCountdown(): string {
  const s = status.value;
  if (!s || !s.nextRunAt) return '—';
  const target = new Date(s.nextRunAt).getTime();
  const diff = target - now.value;
  if (diff <= 0) return '即将开始';
  const mins = Math.floor(diff / 60000);
  const secs = Math.floor((diff % 60000) / 1000);
  return `${mins}m ${secs}s`;
}

onMounted(() => {
  load();
  timer = setInterval(() => {
    now.value = Date.now();
    // 静默轮询：不动 loading，不打断用户编辑
    if (!loading.value) load(true);
  }, 2000);
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<template>
  <div class="page">
    <el-page-header :icon="Promotion" title="返回" @back="$router.push('/dashboard')">
      <template #content>
        <span class="page-title">匹配任务管理</span>
      </template>
    </el-page-header>

    <el-skeleton v-if="loading" :rows="4" animated />
    <el-result v-else-if="errorMessage" icon="error" title="匹配状态加载失败" :sub-title="errorMessage">
      <template #extra><el-button type="primary" @click="load()">重试</el-button></template>
    </el-result>

    <template v-else>
      <!-- 当前状态 -->
      <el-card shadow="never">
        <template #header>
          <div class="head-row">
            <div>
              <el-icon color="#0d4f4f"><Timer /></el-icon>
              <strong>当前状态</strong>
            </div>
            <div class="head-actions">
              <el-button
                type="primary"
                :icon="Refresh"
                :loading="triggering"
                :disabled="isRunning || intervalSaving || triggering"
                @click="triggerRun"
              >
                {{ isRunning ? '正在运行…' : '手动触发匹配' }}
              </el-button>
            </div>
          </div>
        </template>

        <el-descriptions :column="3" border>
          <el-descriptions-item label="任务状态">
            <el-tag :type="statusTagType(status?.status)">
              {{ statusLabel(status?.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="自动间隔">
            {{ status?.intervalMinutes ? `${status.intervalMinutes} 分钟` : '已关闭（仅手动）' }}
          </el-descriptions-item>
          <el-descriptions-item label="下次自动运行">
            {{ nextRunCountdown() }}
          </el-descriptions-item>
          <el-descriptions-item label="上次开始">
            {{ status?.lastRunStartedAt ? shortDateTime(status.lastRunStartedAt) : '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="上次结束">
            {{ status?.lastRunFinishedAt ? shortDateTime(status.lastRunFinishedAt) : '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="上次写入匹配数">
            {{ status?.lastRunWrittenMatches ?? 0 }}
          </el-descriptions-item>
          <el-descriptions-item v-if="status?.lastError" label="上次错误" :span="3">
            <span class="error-text">{{ status.lastError }}</span>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 进度条 -->
        <div v-if="isRunning" class="progress-row">
          <div class="progress-label">
            <span>正在评分</span>
            <span>
              {{ status?.processedPairs ?? 0 }} / {{ status?.totalPairs ?? 0 }} 对
              · 已写入 {{ status?.writtenMatches ?? 0 }} 条
            </span>
          </div>
          <el-progress :percentage="progressPercent" :stroke-width="14" striped striped-flow />
        </div>
      </el-card>

      <!-- 间隔设置 -->
      <el-card shadow="never">
        <template #header>
          <div class="head-row">
            <div>
              <el-icon color="#7c3aed"><Setting /></el-icon>
              <strong>自动匹配设置</strong>
            </div>
          </div>
        </template>

        <div class="interval-row">
          <span>每</span>
          <el-input-number
            :model-value="intervalInput"
            :min="0"
            :max="1440"
            :step="5"
            :disabled="intervalSaving || triggering"
            controls-position="right"
            style="width: 140px"
            @update:model-value="onIntervalInput"
          />
          <span>分钟自动运行一次（填 0 关闭自动，仅手动触发）</span>
          <el-button type="primary" :loading="intervalSaving" :disabled="intervalSaving || triggering" @click="saveInterval">
            保存
          </el-button>
        </div>

        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="说明"
          description="匹配会对所有寻物中的失物与待认领的招领两两评分，总分 ≥ 70 才写入匹配结果。自动运行间隔为 0 时仅靠管理员手动触发，避免无人时浪费 AI 调用配额。"
        />
      </el-card>
    </template>
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-title {
  font-weight: 600;
  font-size: 16px;
}

.head-row {
  display: flex;
  align-items: center;
  justify-content: space-between;

  div {
    display: flex;
    align-items: center;
    gap: 8px;
    strong {
      font-weight: 600;
      font-size: 15px;
    }
  }
}

.progress-row {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;

  .progress-label {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    color: var(--xunji-text-muted);
  }
}

.interval-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.error-text {
  color: var(--el-color-danger);
  font-family: ui-monospace, monospace;
  font-size: 12px;
  word-break: break-all;
}
</style>
