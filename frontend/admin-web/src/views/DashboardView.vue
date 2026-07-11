<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  ChatLineRound,
  Document,
  Medal,
  TrendCharts,
  User,
  Warning,
} from '@element-plus/icons-vue';

import { getDashboard, listCertifications, listReports } from '@/api/admin';
import { ApiError, isUnauthorizedApiError } from '@/api/http';
import StatusTag from '@/components/StatusTag.vue';
import type { CertificationReview, DashboardStats, ReportRecord } from '@xunji/shared';
import { shortDateTime } from '@/utils/format';
import { createLatestRequestGuard } from '@/utils/admin-list';

const router = useRouter();
const stats = ref<DashboardStats | null>(null);
const pendingCerts = ref<CertificationReview[]>([]);
const pendingReports = ref<ReportRecord[]>([]);
const statsLoading = ref(true);
const certsLoading = ref(true);
const reportsLoading = ref(true);
const statsError = ref('');
const certsError = ref('');
const reportsError = ref('');
const statsGuard = createLatestRequestGuard();
const certsGuard = createLatestRequestGuard();
const reportsGuard = createLatestRequestGuard();

function errorText(err: unknown, fallback: string) {
  return err instanceof ApiError ? err.message : fallback;
}

async function loadStats() {
  const requestId = statsGuard.next();
  statsLoading.value = true;
  statsError.value = '';
  try {
    const data = await getDashboard();
    if (statsGuard.isLatest(requestId)) stats.value = data;
  } catch (err) {
    if (!statsGuard.isLatest(requestId) || isUnauthorizedApiError(err)) return;
    stats.value = null;
    statsError.value = errorText(err, '统计数据加载失败');
  } finally {
    if (statsGuard.isLatest(requestId)) statsLoading.value = false;
  }
}

async function loadCerts() {
  const requestId = certsGuard.next();
  certsLoading.value = true;
  certsError.value = '';
  try {
    const data = await listCertifications({ pageSize: 5, reviewStatus: 'PENDING' });
    if (certsGuard.isLatest(requestId)) pendingCerts.value = data.list;
  } catch (err) {
    if (!certsGuard.isLatest(requestId) || isUnauthorizedApiError(err)) return;
    pendingCerts.value = [];
    certsError.value = errorText(err, '待审批认证加载失败');
  } finally {
    if (certsGuard.isLatest(requestId)) certsLoading.value = false;
  }
}

async function loadReports() {
  const requestId = reportsGuard.next();
  reportsLoading.value = true;
  reportsError.value = '';
  try {
    const data = await listReports({ pageSize: 5, handleStatus: 'PENDING' });
    if (reportsGuard.isLatest(requestId)) pendingReports.value = data.list;
  } catch (err) {
    if (!reportsGuard.isLatest(requestId) || isUnauthorizedApiError(err)) return;
    pendingReports.value = [];
    reportsError.value = errorText(err, '待处理举报加载失败');
  } finally {
    if (reportsGuard.isLatest(requestId)) reportsLoading.value = false;
  }
}

onMounted(() => {
  void loadStats();
  void loadCerts();
  void loadReports();
});
</script>

<template>
  <div class="page">
    <el-skeleton v-if="statsLoading" :rows="2" animated />
    <el-card v-else-if="statsError" shadow="never">
      <el-result icon="error" title="统计数据加载失败" :sub-title="statsError">
        <template #extra><el-button type="primary" @click="loadStats">重试</el-button></template>
      </el-result>
    </el-card>
    <section v-else-if="stats" class="stat-grid">
        <el-card shadow="never" class="stat-card">
          <div class="stat-icon" style="background: rgba(13,79,79,0.12); color:#0d4f4f;">
            <el-icon :size="22"><User /></el-icon>
          </div>
          <div>
            <span>用户总数</span>
            <strong>{{ stats?.totalUsers ?? 0 }}</strong>
          </div>
        </el-card>
        <el-card shadow="never" class="stat-card">
          <div class="stat-icon" style="background: rgba(124,58,237,0.12); color:#7c3aed;">
            <el-icon :size="22"><Document /></el-icon>
          </div>
          <div>
            <span>失物 / 招领</span>
            <strong>{{ stats?.totalLost ?? 0 }} / {{ stats?.totalFound ?? 0 }}</strong>
          </div>
        </el-card>
        <el-card shadow="never" class="stat-card">
          <div class="stat-icon" style="background: rgba(20,184,166,0.12); color:#14b8a6;">
            <el-icon :size="22"><TrendCharts /></el-icon>
          </div>
          <div>
            <span>找回率</span>
            <strong>{{ stats?.recoveryRate ?? 0 }}%</strong>
          </div>
        </el-card>
        <el-card shadow="never" class="stat-card">
          <div class="stat-icon" style="background: rgba(245,158,11,0.12); color:#f59e0b;">
            <el-icon :size="22"><ChatLineRound /></el-icon>
          </div>
          <div>
            <span>平均处理时长</span>
            <strong>{{ stats?.avgHandleHours ?? 0 }}h</strong>
          </div>
        </el-card>
    </section>

    <section class="grid-2">
        <el-card shadow="never">
          <template #header>
            <div class="head-row">
              <div>
                <el-icon color="#7c3aed"><Medal /></el-icon>
                <strong>待审批认证</strong>
              </div>
              <el-button link type="primary" @click="router.push('/certifications')">
                查看全部
              </el-button>
            </div>
          </template>
          <el-skeleton v-if="certsLoading" :rows="4" animated />
          <el-result v-else-if="certsError" icon="error" title="待审批认证加载失败" :sub-title="certsError">
            <template #extra><el-button type="primary" @click="loadCerts">重试</el-button></template>
          </el-result>
          <el-table
            v-else-if="pendingCerts.length"
            :data="pendingCerts"
            stripe
            style="width: 100%"
            row-class-name="row-clickable"
            @row-click="router.push('/certifications')"
          >
            <el-table-column prop="realName" label="姓名" width="100" />
            <el-table-column prop="campusId" label="校园编号" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <StatusTag variant="review" :value="row.reviewStatus" />
              </template>
            </el-table-column>
            <el-table-column prop="createdAt" label="提交时间" width="160">
              <template #default="{ row }">{{ shortDateTime(row.createdAt) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="当前没有待审批认证" :image-size="80" />
        </el-card>

        <el-card shadow="never">
          <template #header>
            <div class="head-row">
              <div>
                <el-icon color="#ef4444"><Warning /></el-icon>
                <strong>待处理举报</strong>
              </div>
              <el-button link type="primary" @click="router.push('/reports')">
                查看全部
              </el-button>
            </div>
          </template>
          <el-skeleton v-if="reportsLoading" :rows="4" animated />
          <el-result v-else-if="reportsError" icon="error" title="待处理举报加载失败" :sub-title="reportsError">
            <template #extra><el-button type="primary" @click="loadReports">重试</el-button></template>
          </el-result>
          <el-table
            v-else-if="pendingReports.length"
            :data="pendingReports"
            stripe
            style="width: 100%"
            row-class-name="row-clickable"
            @row-click="router.push('/reports')"
          >
            <el-table-column prop="reason" label="举报原因" />
            <el-table-column prop="targetType" label="目标" width="120" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <StatusTag variant="report" :value="row.handleStatus" />
              </template>
            </el-table-column>
            <el-table-column prop="createdAt" label="举报时间" width="160">
              <template #default="{ row }">{{ shortDateTime(row.createdAt) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="当前没有待处理举报" :image-size="80" />
        </el-card>
    </section>

    <el-alert
        type="info"
        show-icon
        :closable="false"
        title="温馨提示"
        description="所有认证、内容、举报的处理动作都会自动写入操作日志和站内通知"
    />
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;

  .stat-card :deep(.el-card__body) {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px;
  }

  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: grid;
    place-items: center;
    flex-shrink: 0;
  }
  span {
    color: var(--xunji-text-muted);
    font-size: 12px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }
  strong {
    display: block;
    font-size: 22px;
    font-weight: 700;
    margin-top: 2px;
  }
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
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

:deep(.row-clickable) {
  cursor: pointer;
}

@media (max-width: 1100px) {
  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .grid-2 {
    grid-template-columns: 1fr;
  }
}
</style>
