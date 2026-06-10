<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  Bell,
  ChatLineRound,
  Document,
  Medal,
  TrendCharts,
  User,
  Warning,
} from '@element-plus/icons-vue';

import { getDashboard, listCertifications, listReports } from '@/api/admin';
import { isAuthApiError } from '@/api/http';
import StatusTag from '@/components/StatusTag.vue';
import type { CertificationReview, DashboardStats, ReportRecord } from '@xunji/shared';
import { shortDateTime } from '@/utils/format';

const router = useRouter();
const stats = ref<DashboardStats | null>(null);
const pendingCerts = ref<CertificationReview[]>([]);
const pendingReports = ref<ReportRecord[]>([]);
const loading = ref(true);

async function load() {
  loading.value = true;
  try {
    const [s, c, r] = await Promise.all([
      getDashboard(),
      listCertifications({ pageSize: 5, reviewStatus: 'PENDING' }),
      listReports({ pageSize: 5, handleStatus: 'PENDING' }),
    ]);
    stats.value = s;
    pendingCerts.value = c.list;
    pendingReports.value = r.list;
  } catch (err) {
    if (isAuthApiError(err)) return;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="page">
    <el-skeleton v-if="loading" :rows="4" animated />

    <template v-else>
      <section class="stat-grid">
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
          <el-table
            v-if="pendingCerts.length"
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
          <el-table
            v-if="pendingReports.length"
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
    </template>
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
