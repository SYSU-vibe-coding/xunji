<script setup lang="ts">
import { computed, onMounted, reactive, ref, type Component } from 'vue';
import {
  ArrowRight,
  BadgeCheck,
  BarChart3,
  BellPlus,
  Building2,
  CheckCircle2,
  ChevronRight,
  FileWarning,
  LayoutDashboard,
  LogOut,
  Megaphone,
  Search,
  ShieldAlert,
  UserCog,
  XCircle,
} from 'lucide-vue-next';

import { useAdminNavigationStore, type AdminPage } from '@/stores/navigation';
import {
  AdminApiError,
  changeAdminUserStatus,
  clearStoredAdminToken,
  createAnnouncement,
  getDashboard,
  getStoredAdminToken,
  handleAdminReport,
  listAdminUsers,
  listCertifications,
  listItemReviews,
  listReports,
  loginAdminWithPassword,
  reviewCertification,
  reviewItem,
} from '@/api/client';
import {
  type AdminUserRecord,
  type CertificationReview,
  categoryLabels,
  certStatusLabels,
  type DashboardStats,
  foundStatusLabels,
  type ItemReviewRecord,
  lostStatusLabels,
  type ReportRecord,
  reportStatusLabels,
  reviewStatusLabels,
  userRoleLabels,
  userStatusLabels,
} from '@xunji/shared';

const navigation = useAdminNavigationStore();
const actionNote = ref('');
const loadState = ref('');
const isAuthenticated = ref(Boolean(getStoredAdminToken()));
const isAdminRole = ref(false);
const authError = ref('');
const isLoggingIn = ref(false);
const certificationComment = ref('资料清晰，身份信息与校园编号一致');
const rejectComment = ref('请补充清晰证件照后重新提交');
const reportResult = ref('举报有效，已扣减信用分并通知当事人');
const userKeyword = ref('');
const emptyDashboardStats: DashboardStats = {
  totalUsers: 0,
  totalLost: 0,
  totalFound: 0,
  handedOverCount: 0,
  recoveryRate: 0,
  avgHandleHours: 0,
  pendingCertifications: 0,
  pendingReports: 0,
};
const dashboardStats = ref<DashboardStats>(emptyDashboardStats);
const certifications = ref<CertificationReview[]>([]);
const itemReviews = ref<ItemReviewRecord[]>([]);
const reports = ref<ReportRecord[]>([]);
const adminUsers = ref<AdminUserRecord[]>([]);

const loginForm = reactive({
  account: '',
  password: '',
});

const announcement = reactive({
  title: '本周长期未领物品清单',
  content: '请相关同学在工作日前往保卫处证件窗口核验领取。',
  publishNow: true,
});

const navItems: Array<{ key: AdminPage; label: string; icon: Component }> = [
  { key: 'dashboard', label: '总览', icon: LayoutDashboard },
  { key: 'certifications', label: '认证', icon: BadgeCheck },
  { key: 'content', label: '内容', icon: FileWarning },
  { key: 'reports', label: '举报', icon: ShieldAlert },
  { key: 'announcements', label: '公告', icon: Megaphone },
  { key: 'users', label: '用户', icon: UserCog },
];

const activeTitle = computed(() => navItems.find((item) => item.key === navigation.activePage)?.label ?? '管理后台');
const activeTabIndex = computed(() => Math.max(0, navItems.findIndex((item) => item.key === navigation.activePage)));
const mobileDockIndicatorStyle = computed(() => ({
  width: `calc((100% - 16px - ${(navItems.length - 1) * 4}px) / ${navItems.length})`,
  transform: `translateX(calc(${activeTabIndex.value} * (100% + 4px)))`,
}));
const canLogin = computed(() => loginForm.account.trim().length >= 3 && loginForm.password.length >= 6 && !isLoggingIn.value);
const canSubmitAnnouncement = computed(() => Boolean(announcement.title.trim() && announcement.content.trim()));
const statCards = computed(() => [
  { label: '用户总数', value: dashboardStats.value.totalUsers, note: '认证、普通和后台角色' },
  { label: '失物 / 招领', value: `${dashboardStats.value.totalLost} / ${dashboardStats.value.totalFound}`, note: '当前累计发布' },
  { label: '找回率', value: `${dashboardStats.value.recoveryRate}%`, note: `${dashboardStats.value.handedOverCount} 次已交接` },
  { label: '平均处理', value: `${dashboardStats.value.avgHandleHours}h`, note: '发布到交接平均时长' },
]);

const filteredUsers = computed(() => {
  const keyword = userKeyword.value.trim().toLowerCase();
  if (!keyword) return adminUsers.value;
  return adminUsers.value.filter(
    (user) =>
      user.nickname.toLowerCase().includes(keyword) ||
      user.phone.toLowerCase().includes(keyword) ||
      user.id.toLowerCase().includes(keyword),
  );
});

function itemStatusLabel(record: ItemReviewRecord): string {
  return record.bizType === 'FOUND'
    ? foundStatusLabels[record.status as keyof typeof foundStatusLabels]
    : lostStatusLabels[record.status as keyof typeof lostStatusLabels];
}

function bizTypeLabel(value: ItemReviewRecord['bizType']): string {
  return value === 'FOUND' ? '招领' : '失物';
}

function go(page: AdminPage) {
  navigation.go(page);
}

async function submitAdminLogin() {
  authError.value = '';
  if (!canLogin.value) {
    authError.value = '账号或密码不正确';
    return;
  }
  isLoggingIn.value = true;
  try {
    const data = await loginAdminWithPassword(loginForm.account.trim(), loginForm.password);
    if (data.user.role !== 'ADMIN') {
      clearStoredAdminToken();
      isAuthenticated.value = false;
      isAdminRole.value = false;
      resetEmptyData();
      authError.value = '无后台权限';
      return;
    }
    isAuthenticated.value = true;
    isAdminRole.value = true;
    await loadAdminData();
  } catch (error) {
    authError.value = error instanceof Error ? error.message : '登录失败';
  } finally {
    isLoggingIn.value = false;
  }
}

function logout() {
  clearStoredAdminToken();
  isAuthenticated.value = false;
  isAdminRole.value = false;
}

async function loadAdminData() {
  try {
    const [dashboard, certPage, itemPage, reportPage, userPage] = await Promise.all([
      getDashboard(),
      listCertifications(),
      listItemReviews(),
      listReports(),
      listAdminUsers(userKeyword.value.trim()),
    ]);
    dashboardStats.value = dashboard;
    certifications.value = certPage.list;
    itemReviews.value = itemPage.list;
    reports.value = reportPage.list;
    adminUsers.value = userPage.list;
    isAdminRole.value = true;
    loadState.value = `认证 ${certPage.total} · 举报 ${reportPage.total} · 用户 ${userPage.total}`;
  } catch (error) {
    if (error instanceof AdminApiError && (error.code === 40002 || error.code === 48002)) {
      clearStoredAdminToken();
      isAuthenticated.value = false;
      isAdminRole.value = false;
      resetEmptyData();
      loadState.value = '登录已失效，请重新登录';
      return;
    }
    loadState.value = '服务暂不可用';
    resetEmptyData();
  }
}

function resetEmptyData() {
  dashboardStats.value = { ...emptyDashboardStats };
  certifications.value = [];
  itemReviews.value = [];
  reports.value = [];
  adminUsers.value = [];
}

async function approveCertification(record: CertificationReview) {
  actionNote.value = '处理中';
  try {
    await reviewCertification(record.id, {
      action: 'APPROVE',
      comment: certificationComment.value,
    });
    actionNote.value = `已通过 ${record.realName}`;
    await loadAdminData();
  } catch (error) {
    actionNote.value = error instanceof Error ? error.message : '处理失败';
  }
}

async function rejectCertification(record: CertificationReview) {
  actionNote.value = '处理中';
  try {
    await reviewCertification(record.id, {
      action: 'REJECT',
      comment: rejectComment.value,
    });
    actionNote.value = `已驳回 ${record.realName}`;
    await loadAdminData();
  } catch (error) {
    actionNote.value = error instanceof Error ? error.message : '处理失败';
  }
}

async function approveContent(record: ItemReviewRecord) {
  actionNote.value = '处理中';
  try {
    await reviewItem(record.bizType, record.id, { action: 'APPROVE' });
    actionNote.value = `已通过 ${record.itemName}`;
    await loadAdminData();
  } catch (error) {
    actionNote.value = error instanceof Error ? error.message : '处理失败';
  }
}

async function rejectContent(record: ItemReviewRecord) {
  actionNote.value = '处理中';
  try {
    await reviewItem(record.bizType, record.id, { action: 'REJECT', comment: '内容不符合发布要求' });
    actionNote.value = `已关闭 ${record.itemName}`;
    await loadAdminData();
  } catch (error) {
    actionNote.value = error instanceof Error ? error.message : '处理失败';
  }
}

async function handleReport(record: ReportRecord, valid: boolean) {
  actionNote.value = '处理中';
  try {
    await handleAdminReport(record.id, {
      action: valid ? 'VALID' : 'INVALID',
      result: valid ? reportResult.value : '举报依据不足',
      ...(valid ? { creditDelta: -10, reasonCode: 'REPORT_VALID' } : {}),
    });
    actionNote.value = valid ? `已处理举报：${record.reason}` : `已驳回举报：${record.reason}`;
    await loadAdminData();
  } catch (error) {
    actionNote.value = error instanceof Error ? error.message : '处理失败';
  }
}

async function toggleUserStatus(record: AdminUserRecord) {
  actionNote.value = '处理中';
  const nextStatus = record.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE';
  try {
    await changeAdminUserStatus(record.id, {
      status: nextStatus,
      reason: nextStatus === 'DISABLED' ? '后台风控处理' : '后台恢复账号',
    });
    actionNote.value = `${record.nickname} 已更新为 ${userStatusLabels[nextStatus]}`;
    await loadAdminData();
  } catch (error) {
    actionNote.value = error instanceof Error ? error.message : '处理失败';
  }
}

function submitAnnouncement() {
  actionNote.value = '公告提交中...';
  createAnnouncement({
    title: announcement.title,
    content: announcement.content,
    publishNow: announcement.publishNow,
  })
    .then((result) => {
      actionNote.value = `公告已提交，状态：${result.status}`;
    })
    .catch((error: unknown) => {
      actionNote.value =
        error instanceof Error
          ? `公告提交失败，已保留本地草稿：${error.message}`
          : `公告草稿已生成：${announcement.title}`;
    });
}

onMounted(async () => {
  if (isAuthenticated.value) {
    await loadAdminData();
  }
});
</script>

<template>
  <div class="admin-frame" :class="{ 'auth-mode': !isAuthenticated }">
    <section v-if="!isAuthenticated" class="auth-view">
      <div class="auth-hero">
        <div class="brand-lockup">
          <span class="brand-mark"><Building2 :size="22" /></span>
          <span>
            <strong>寻迹后台</strong>
            <small>Admin Console</small>
          </span>
        </div>
        <div class="auth-copy">
          <span class="eyebrow">Operations</span>
          <h1>管理后台</h1>
          <p>认证、内容、举报、公告统一处理。</p>
        </div>
        <div class="feature-list">
          <span><BadgeCheck :size="16" />身份审批</span>
          <span><FileWarning :size="16" />内容治理</span>
          <span><ShieldAlert :size="16" />风险处理</span>
        </div>
      </div>

      <form class="auth-card" @submit.prevent="submitAdminLogin">
        <div class="card-header">
          <span class="eyebrow">Admin sign in</span>
          <h2>后台登录</h2>
        </div>

        <div class="field-group">
          <label class="field">
            <span>账号</span>
            <input v-model="loginForm.account" autocomplete="username" placeholder="admin" />
          </label>
          <label class="field">
            <span>密码</span>
            <input v-model="loginForm.password" type="password" autocomplete="current-password" placeholder="至少 6 位" />
          </label>
        </div>

        <p v-if="authError" class="alert alert-danger"><XCircle :size="17" />{{ authError }}</p>

        <button class="button button-primary button-block" type="submit" :disabled="!canLogin">
          {{ isLoggingIn ? '登录中' : '登录' }}
          <ArrowRight :size="17" />
        </button>
      </form>
    </section>

    <template v-else>
      <aside class="admin-sidebar" aria-label="管理端主导航">
        <div class="brand-lockup">
          <span class="brand-mark"><Building2 :size="22" /></span>
          <span>
            <strong>寻迹后台</strong>
            <small>Admin Console</small>
          </span>
        </div>

        <nav class="sidebar-nav">
          <button
            v-for="item in navItems"
            :key="item.key"
            type="button"
            :class="{ active: navigation.activePage === item.key }"
            :aria-current="navigation.activePage === item.key ? 'page' : undefined"
            @click="go(item.key)"
          >
            <component :is="item.icon" :size="19" />
            <span>{{ item.label }}</span>
          </button>
        </nav>

        <button type="button" class="sidebar-exit" @click="logout">
          <LogOut :size="18" />
          退出登录
        </button>
      </aside>

      <div class="admin-main">
        <header class="admin-topbar">
          <div>
            <span class="eyebrow">寻迹管理后台</span>
            <h1>{{ activeTitle }}</h1>
          </div>
          <div class="top-actions">
            <span v-if="loadState" class="backend-state">{{ loadState }}</span>
            <button type="button" class="icon-button" aria-label="全局搜索"><Search :size="19" /></button>
            <button type="button" class="icon-button" aria-label="发布公告" @click="go('announcements')"><BellPlus :size="19" /></button>
            <button type="button" class="icon-button danger" aria-label="退出登录" @click="logout"><LogOut :size="19" /></button>
          </div>
        </header>

        <main class="admin-content">
          <Transition name="page-transition" mode="out-in">
            <section v-if="navigation.activePage === 'dashboard'" key="dashboard" class="page-stack">
              <div class="stat-grid">
                <article v-for="stat in statCards" :key="stat.label" class="stat-card">
                  <span>{{ stat.label }}</span>
                  <strong>{{ stat.value }}</strong>
                  <small>{{ stat.note }}</small>
                </article>
              </div>

              <div class="workbench-grid">
                <article class="card">
                  <div class="card-header horizontal">
                    <div>
                      <span class="eyebrow">身份认证</span>
                      <h2>待审批认证</h2>
                    </div>
                    <span class="badge">{{ dashboardStats.pendingCertifications }}</span>
                  </div>
                  <div class="queue-list">
                    <div v-for="record in certifications" :key="record.id" class="queue-row">
                      <span class="avatar">{{ record.realName.slice(0, 1) }}</span>
                      <div>
                        <strong>{{ record.realName }}</strong>
                        <small>{{ record.campusId }} · {{ record.createdAt }}</small>
                      </div>
                      <button type="button" class="button button-secondary" @click="go('certifications')">处理</button>
                    </div>
                    <div v-if="!certifications.length" class="empty-state compact">
                      <BadgeCheck :size="22" />
                      <strong>暂无待审批认证</strong>
                    </div>
                  </div>
                </article>

                <article class="card">
                  <div class="card-header horizontal">
                    <div>
                      <span class="eyebrow">举报处理</span>
                      <h2>举报风险</h2>
                    </div>
                    <span class="badge badge-warning">{{ dashboardStats.pendingReports }}</span>
                  </div>
                  <div class="queue-list">
                    <div v-for="record in reports" :key="record.id" class="queue-row">
                      <span class="queue-icon warning"><ShieldAlert :size="22" /></span>
                      <div>
                        <strong>{{ record.reason }}</strong>
                        <small>{{ reportStatusLabels[record.handleStatus] }} · {{ record.createdAt }}</small>
                      </div>
                      <button type="button" class="button button-secondary" @click="go('reports')">处理</button>
                    </div>
                    <div v-if="!reports.length" class="empty-state compact">
                      <ShieldAlert :size="22" />
                      <strong>暂无举报风险</strong>
                    </div>
                  </div>
                </article>
              </div>
            </section>

            <section v-else-if="navigation.activePage === 'certifications'" key="certifications" class="page-stack">
              <div class="card action-card">
                <label class="field">
                  <span>通过说明</span>
                  <input v-model="certificationComment" />
                </label>
                <label class="field">
                  <span>驳回原因</span>
                  <input v-model="rejectComment" />
                </label>
              </div>

              <table class="record-table">
                <thead>
                  <tr>
                    <th>申请人</th>
                    <th>校园编号</th>
                    <th>审核状态</th>
                    <th>提交时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="record in certifications" :key="record.id">
                    <td>
                      <strong>{{ record.realName }}</strong>
                      <span>{{ record.nickname }} · {{ record.userId }}</span>
                    </td>
                    <td>{{ record.campusId }}</td>
                    <td><span class="badge">{{ reviewStatusLabels[record.reviewStatus] }}</span></td>
                    <td>{{ record.createdAt }}</td>
                    <td>
                      <div class="row-actions">
                        <button type="button" class="button button-approve" @click="approveCertification(record)">
                          <CheckCircle2 :size="16" />通过
                        </button>
                        <button type="button" class="button button-danger" @click="rejectCertification(record)">
                          <XCircle :size="16" />驳回
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>

              <div class="record-list">
                <article v-for="record in certifications" :key="record.id" class="card record-card">
                  <div class="record-title">
                    <strong>{{ record.realName }}</strong>
                    <span class="badge">{{ reviewStatusLabels[record.reviewStatus] }}</span>
                  </div>
                  <p>{{ record.nickname }} · {{ record.campusId }}</p>
                  <p>{{ record.createdAt }}</p>
                  <div class="row-actions">
                    <button type="button" class="button button-approve" @click="approveCertification(record)">
                      <CheckCircle2 :size="16" />通过
                    </button>
                    <button type="button" class="button button-danger" @click="rejectCertification(record)">
                      <XCircle :size="16" />驳回
                    </button>
                  </div>
                </article>
              </div>
              <div v-if="!certifications.length" class="empty-state">
                <BadgeCheck :size="24" />
                <strong>暂无认证申请</strong>
              </div>
            </section>

            <section v-else-if="navigation.activePage === 'content'" key="content" class="page-stack">
              <div class="section-heading card">
                <div>
                  <span class="eyebrow">Item Review</span>
                  <h2>失物 / 招领内容审核</h2>
                </div>
                <span class="badge">{{ itemReviews.length }}</span>
              </div>

              <table class="record-table">
                <thead>
                  <tr>
                    <th>业务类型</th>
                    <th>物品名称</th>
                    <th>类别</th>
                    <th>地点</th>
                    <th>状态</th>
                    <th>举报数</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="record in itemReviews" :key="record.id">
                    <td>{{ bizTypeLabel(record.bizType) }}</td>
                    <td>
                      <strong>{{ record.itemName }}</strong>
                      <span>{{ record.ownerNickname }} · {{ record.createdAt }}</span>
                    </td>
                    <td>{{ categoryLabels[record.category] }}</td>
                    <td>{{ record.location }}</td>
                    <td><span class="badge">{{ itemStatusLabel(record) }}</span></td>
                    <td>{{ record.reportCount }}</td>
                    <td>
                      <div class="row-actions">
                        <button type="button" class="button button-approve" @click="approveContent(record)">通过</button>
                        <button type="button" class="button button-danger" @click="rejectContent(record)">关闭</button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>

              <div class="record-list">
                <article v-for="record in itemReviews" :key="record.id" class="card record-card">
                  <div class="record-title">
                    <strong>{{ record.itemName }}</strong>
                    <span class="badge">{{ bizTypeLabel(record.bizType) }}</span>
                  </div>
                  <p>{{ categoryLabels[record.category] }} · {{ record.location }}</p>
                  <p>{{ itemStatusLabel(record) }} · 举报 {{ record.reportCount }}</p>
                  <div class="row-actions">
                    <button type="button" class="button button-approve" @click="approveContent(record)">通过</button>
                    <button type="button" class="button button-danger" @click="rejectContent(record)">关闭</button>
                  </div>
                </article>
              </div>
              <div v-if="!itemReviews.length" class="empty-state">
                <FileWarning :size="24" />
                <strong>暂无内容审核记录</strong>
              </div>
            </section>

            <section v-else-if="navigation.activePage === 'reports'" key="reports" class="page-stack">
              <article class="card action-card single">
                <label class="field">
                  <span>有效举报处理结果</span>
                  <input v-model="reportResult" />
                </label>
              </article>

              <div class="report-grid">
                <article v-for="record in reports" :key="record.id" class="card report-card">
                  <div class="card-header horizontal">
                    <div>
                      <span class="eyebrow">{{ record.targetType }}</span>
                      <h2>{{ record.reason }}</h2>
                    </div>
                    <span class="badge badge-warning">{{ reportStatusLabels[record.handleStatus] }}</span>
                  </div>
                  <p>{{ record.description }}</p>
                  <dl>
                    <div>
                      <dt>举报人 ID</dt>
                      <dd>{{ record.reporterId }}</dd>
                    </div>
                    <div>
                      <dt>被举报人 ID</dt>
                      <dd>{{ record.reportedUserId }}</dd>
                    </div>
                    <div>
                      <dt>目标 ID</dt>
                      <dd>{{ record.targetId }}</dd>
                    </div>
                  </dl>
                  <div class="row-actions">
                    <button type="button" class="button button-approve" @click="handleReport(record, true)">有效</button>
                    <button type="button" class="button button-danger" @click="handleReport(record, false)">无效</button>
                  </div>
                </article>
              </div>
              <div v-if="!reports.length" class="empty-state">
                <ShieldAlert :size="24" />
                <strong>暂无举报记录</strong>
              </div>
            </section>

            <section v-else-if="navigation.activePage === 'announcements'" key="announcements" class="page-stack">
              <form class="card form-card" @submit.prevent="submitAnnouncement">
                <div class="card-header">
                  <span class="eyebrow">Announcement</span>
                  <h2>发布公告</h2>
                </div>
                <label class="field">
                  <span>公告标题</span>
                  <input v-model="announcement.title" required maxlength="100" />
                </label>
                <label class="field">
                  <span>公告内容</span>
                  <textarea v-model="announcement.content" required maxlength="5000" rows="9" />
                </label>
                <label class="switch-row">
                  <input v-model="announcement.publishNow" type="checkbox" />
                  <span>
                    <strong>立即发布</strong>
                  </span>
                </label>
                <button class="button button-primary" type="submit" :disabled="!canSubmitAnnouncement">
                  <Megaphone :size="18" />发布公告
                </button>
              </form>
            </section>

            <section v-else key="users" class="page-stack">
              <label class="search-field">
                <Search :size="18" />
                <input v-model="userKeyword" placeholder="手机号、昵称、用户 ID" />
              </label>

              <table class="record-table">
                <thead>
                  <tr>
                    <th>用户</th>
                    <th>角色</th>
                    <th>认证状态</th>
                    <th>信誉分</th>
                    <th>账号状态</th>
                    <th>最近时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="record in filteredUsers" :key="record.id">
                    <td>
                      <strong>{{ record.nickname }}</strong>
                      <span>{{ record.phone }} · {{ record.id }}</span>
                    </td>
                    <td>{{ userRoleLabels[record.role] }}</td>
                    <td>{{ certStatusLabels[record.certStatus] }}</td>
                    <td>{{ record.creditScore }}</td>
                    <td><span class="badge">{{ userStatusLabels[record.status] }}</span></td>
                    <td>{{ record.lastActiveAt ?? record.createdAt ?? '暂无记录' }}</td>
                    <td>
                      <button type="button" class="button button-danger" :disabled="record.role === 'ADMIN'" @click="toggleUserStatus(record)">
                        {{ record.role === 'ADMIN' ? '管理员' : record.status === 'ACTIVE' ? '禁用' : '启用' }}
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>

              <div class="record-list">
                <article v-for="record in filteredUsers" :key="record.id" class="card record-card">
                  <div class="record-title">
                    <strong>{{ record.nickname }}</strong>
                    <span class="badge">{{ userStatusLabels[record.status] }}</span>
                  </div>
                  <p>{{ record.phone }} · {{ userRoleLabels[record.role] }}</p>
                  <p>{{ certStatusLabels[record.certStatus] }} · {{ record.creditScore }} 分</p>
                  <button type="button" class="button button-danger" :disabled="record.role === 'ADMIN'" @click="toggleUserStatus(record)">
                    {{ record.role === 'ADMIN' ? '管理员' : record.status === 'ACTIVE' ? '禁用' : '启用' }}
                  </button>
                </article>
              </div>
              <div v-if="!filteredUsers.length" class="empty-state">
                <UserCog :size="24" />
                <strong>暂无用户记录</strong>
              </div>
            </section>
          </Transition>

          <p v-if="actionNote" class="action-note"><BarChart3 :size="18" />{{ actionNote }}</p>
        </main>
      </div>

      <nav class="mobile-dock" aria-label="移动端管理导航">
        <span class="dock-indicator" :style="mobileDockIndicatorStyle"></span>
        <button
          v-for="item in navItems"
          :key="item.key"
          type="button"
          :class="{ active: navigation.activePage === item.key }"
          :aria-current="navigation.activePage === item.key ? 'page' : undefined"
          @click="go(item.key)"
        >
          <component :is="item.icon" :size="19" />
          <span>{{ item.label }}</span>
        </button>
      </nav>
    </template>
  </div>
</template>
