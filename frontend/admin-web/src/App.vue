<script setup lang="ts">
import { computed, onMounted, reactive, ref, type Component } from 'vue';
import {
  BadgeCheck,
  BarChart3,
  BellPlus,
  Building2,
  CheckCircle2,
  FileWarning,
  LayoutDashboard,
  Megaphone,
  Search,
  ShieldAlert,
  UserCog,
  XCircle,
} from 'lucide-vue-next';

import { useAdminNavigationStore, type AdminPage } from '@/stores/navigation';
import {
  clearStoredAdminToken,
  createAnnouncement,
  getDashboard,
  getStoredAdminToken,
  listAdminUsers,
  listCertifications,
  listItemReviews,
  listReports,
  loginAdminWithPhoneCode,
  sendAdminSmsCode,
} from '@/api/client';
import {
  type AdminUserRecord,
  type CertificationReview,
  categoryLabels,
  certStatusLabels,
  demoAdminUsers,
  demoCertifications,
  demoDashboardStats,
  demoItemReviews,
  demoReports,
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
const loadState = ref('后端未连接时自动使用演示数据');
const isAuthenticated = ref(Boolean(getStoredAdminToken()));
const isAdminRole = ref(false);
const authError = ref('');
const smsHint = ref('');
const certificationComment = ref('资料清晰，身份信息与校园编号一致');
const rejectComment = ref('请补充清晰证件照后重新提交');
const reportResult = ref('举报有效，已扣减信用分并通知当事人');
const userKeyword = ref('');
const dashboardStats = ref<DashboardStats>(demoDashboardStats);
const certifications = ref<CertificationReview[]>(demoCertifications);
const itemReviews = ref<ItemReviewRecord[]>(demoItemReviews);
const reports = ref<ReportRecord[]>(demoReports);
const adminUsers = ref<AdminUserRecord[]>(demoAdminUsers);

const loginForm = reactive({
  phone: '13800000013',
  code: '123456',
});

const announcement = reactive({
  title: '本周长期未领物品清单',
  content: '请相关同学在工作日前往保卫处证件窗口核验领取。',
  publishNow: true,
});

const navItems: Array<{ key: AdminPage; label: string; icon: Component }> = [
  { key: 'dashboard', label: '数据统计', icon: LayoutDashboard },
  { key: 'certifications', label: '身份认证', icon: BadgeCheck },
  { key: 'content', label: '内容审核', icon: FileWarning },
  { key: 'reports', label: '举报处理', icon: ShieldAlert },
  { key: 'announcements', label: '公告管理', icon: Megaphone },
  { key: 'users', label: '用户管理', icon: UserCog },
];

const activeTitle = computed(() => navItems.find((item) => item.key === navigation.activePage)?.label ?? '管理后台');

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

async function requestAdminSmsCode() {
  authError.value = '';
  try {
    const data = await sendAdminSmsCode(loginForm.phone);
    smsHint.value = `验证码已发送，演示码：${data.debugCode ?? loginForm.code}`;
  } catch (error) {
    authError.value = error instanceof Error ? error.message : '验证码发送失败';
  }
}

async function submitAdminLogin() {
  authError.value = '';
  try {
    const data = await loginAdminWithPhoneCode(loginForm.phone, loginForm.code);
    isAuthenticated.value = true;
    isAdminRole.value = data.user.role === 'ADMIN';
    if (!isAdminRole.value) {
      loadState.value = '当前账号不是管理员，后台接口会拒绝访问，页面使用演示数据';
      return;
    }
    await loadAdminData();
  } catch (error) {
    authError.value = error instanceof Error ? error.message : '登录失败';
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
    certifications.value = certPage.list.length ? certPage.list : demoCertifications;
    itemReviews.value = itemPage.list.length ? itemPage.list : demoItemReviews;
    reports.value = reportPage.list.length ? reportPage.list : demoReports;
    adminUsers.value = userPage.list.length ? userPage.list : demoAdminUsers;
    isAdminRole.value = true;
    loadState.value = `已连接后端：认证 ${certPage.total} 条，举报 ${reportPage.total} 条，用户 ${userPage.total} 个`;
  } catch (error) {
    loadState.value = error instanceof Error ? `后台数据加载失败，使用演示数据：${error.message}` : '使用演示数据';
    dashboardStats.value = demoDashboardStats;
    certifications.value = demoCertifications;
    itemReviews.value = demoItemReviews;
    reports.value = demoReports;
    adminUsers.value = demoAdminUsers;
  }
}

function approveCertification(realName: string) {
  actionNote.value = `已准备通过 ${realName} 的认证申请，接口动作：APPROVE`;
}

function rejectCertification(realName: string) {
  actionNote.value = `已准备驳回 ${realName} 的认证申请，comment：${rejectComment.value}`;
}

function approveContent(itemName: string) {
  actionNote.value = `已准备通过 ${itemName} 的内容审核`;
}

function rejectContent(itemName: string) {
  actionNote.value = `已准备关闭 ${itemName} 并通知发布者`;
}

function handleReport(reason: string, valid: boolean) {
  actionNote.value = valid ? `已准备按有效举报处理：${reason}` : `已准备按无效举报驳回：${reason}`;
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
  <div class="admin-frame" :class="{ 'login-mode': !isAuthenticated }">
    <section v-if="!isAuthenticated" class="login-screen">
      <div class="login-visual">
        <div class="brand-lockup">
          <span class="brand-mark"><Building2 :size="21" /></span>
          <div>
            <strong>寻迹后台</strong>
            <small>管理员</small>
          </div>
        </div>
        <h1>管理校园失物招领全流程</h1>
        <p>管理员登录后可处理身份认证、内容审核、举报、公告和用户状态。</p>
        <div class="login-bullets">
          <span><BadgeCheck :size="17" />身份审批</span>
          <span><FileWarning :size="17" />敏感内容审核</span>
          <span><ShieldAlert :size="17" />举报处置</span>
        </div>
      </div>

      <form class="login-card" @submit.prevent="submitAdminLogin">
        <span class="eyebrow">管理员登录</span>
        <h2>管理后台登录</h2>
        <label>
          <span>管理员手机号</span>
          <input v-model="loginForm.phone" inputmode="numeric" maxlength="11" placeholder="请输入管理员手机号" />
        </label>
        <label>
          <span>短信验证码</span>
          <div class="code-row">
            <input v-model="loginForm.code" inputmode="numeric" maxlength="6" placeholder="123456" />
            <button type="button" class="ghost-action" @click="requestAdminSmsCode">获取验证码</button>
          </div>
        </label>
        <p v-if="smsHint" class="form-hint">{{ smsHint }}</p>
        <p v-if="authError" class="form-error">{{ authError }}</p>
        <button class="primary-action" type="submit">登录管理后台</button>
      </form>
    </section>

    <template v-else>
    <aside class="admin-sidebar" aria-label="管理端主导航">
      <div class="brand-lockup">
        <span class="brand-mark"><Building2 :size="21" /></span>
        <div>
          <strong>寻迹后台</strong>
          <small>管理员</small>
        </div>
      </div>

      <nav>
        <button
          v-for="item in navItems"
          :key="item.key"
          type="button"
          :class="{ active: navigation.activePage === item.key }"
          @click="go(item.key)"
        >
          <component :is="item.icon" :size="19" />
          <span>{{ item.label }}</span>
        </button>
      </nav>
    </aside>

    <div class="admin-main">
      <header class="admin-topbar">
        <div>
          <span class="eyebrow">寻迹管理后台</span>
          <h1>{{ activeTitle }}</h1>
        </div>
        <div class="top-actions">
          <span class="backend-state">{{ loadState }}</span>
          <button type="button" class="icon-button" aria-label="全局搜索"><Search :size="19" /></button>
          <button type="button" class="icon-button" aria-label="发布公告" @click="go('announcements')"><BellPlus :size="19" /></button>
          <button type="button" class="icon-button danger" aria-label="退出登录" @click="logout"><XCircle :size="19" /></button>
        </div>
      </header>

      <nav class="mobile-tabs" aria-label="移动端管理导航">
        <button
          v-for="item in navItems"
          :key="item.key"
          type="button"
          :class="{ active: navigation.activePage === item.key }"
          @click="go(item.key)"
        >
          <component :is="item.icon" :size="17" />
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <main class="admin-content">
        <p v-if="!isAdminRole" class="permission-note">
          当前登录账号不是管理员角色，后台接口会返回无权限；下方数据为演示视图。
        </p>

        <section v-if="navigation.activePage === 'dashboard'" class="page-stack">
          <div class="stat-grid">
            <article>
              <span>用户总数</span>
              <strong>{{ dashboardStats.totalUsers }}</strong>
              <small>认证、普通和后台角色</small>
            </article>
            <article>
              <span>失物 / 招领发布量</span>
              <strong>{{ dashboardStats.totalLost }} / {{ dashboardStats.totalFound }}</strong>
              <small>当前累计发布</small>
            </article>
            <article>
              <span>找回率</span>
              <strong>{{ dashboardStats.recoveryRate }}%</strong>
              <small>{{ dashboardStats.handedOverCount }} 次已交接</small>
            </article>
            <article>
              <span>平均处理时长</span>
              <strong>{{ dashboardStats.avgHandleHours }}h</strong>
              <small>发布到交接平均时长</small>
            </article>
          </div>

          <div class="workbench-grid">
            <article class="queue-panel">
              <div class="panel-heading">
                <div>
                  <span class="eyebrow">身份认证</span>
                  <h2>待审批认证</h2>
                </div>
                <span class="count-pill">{{ dashboardStats.pendingCertifications }}</span>
              </div>
              <div class="queue-list">
                <div v-for="record in certifications" :key="record.id" class="queue-row">
                  <span class="avatar">{{ record.realName.slice(0, 1) }}</span>
                  <div>
                    <strong>{{ record.realName }}</strong>
                    <span>{{ record.campusId }} · {{ record.createdAt }}</span>
                  </div>
                  <button type="button" class="ghost-action" @click="go('certifications')">处理</button>
                </div>
              </div>
            </article>

            <article class="queue-panel accent">
              <div class="panel-heading">
                <div>
                  <span class="eyebrow">举报处理</span>
                  <h2>举报风险</h2>
                </div>
                <span class="count-pill warn">{{ dashboardStats.pendingReports }}</span>
              </div>
              <div class="queue-list">
                <div v-for="record in reports" :key="record.id" class="queue-row">
                  <ShieldAlert :size="22" />
                  <div>
                    <strong>{{ record.reason }}</strong>
                    <span>{{ reportStatusLabels[record.handleStatus] }} · {{ record.createdAt }}</span>
                  </div>
                  <button type="button" class="ghost-action" @click="go('reports')">处理</button>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section v-else-if="navigation.activePage === 'certifications'" class="page-stack">
          <div class="action-strip">
            <label>
              <span>通过说明</span>
              <input v-model="certificationComment" />
            </label>
            <label>
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
                <td><span class="status-badge">{{ reviewStatusLabels[record.reviewStatus] }}</span></td>
                <td>{{ record.createdAt }}</td>
                <td>
                  <div class="row-actions">
                    <button type="button" class="approve" @click="approveCertification(record.realName)">
                      <CheckCircle2 :size="16" />通过
                    </button>
                    <button type="button" class="reject" @click="rejectCertification(record.realName)">
                      <XCircle :size="16" />驳回
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>

          <div class="record-list">
            <article v-for="record in certifications" :key="record.id">
              <div class="mobile-record-title">
                <strong>{{ record.realName }}</strong>
                <span class="status-badge">{{ reviewStatusLabels[record.reviewStatus] }}</span>
              </div>
              <p>{{ record.nickname }} · {{ record.campusId }}</p>
              <p>{{ record.createdAt }}</p>
              <div class="row-actions">
                <button type="button" class="approve" @click="approveCertification(record.realName)">
                  <CheckCircle2 :size="16" />通过
                </button>
                <button type="button" class="reject" @click="rejectCertification(record.realName)">
                  <XCircle :size="16" />驳回
                </button>
              </div>
            </article>
          </div>
        </section>

        <section v-else-if="navigation.activePage === 'content'" class="page-stack">
          <div class="section-line">
            <div>
              <span class="eyebrow">ITEM REVIEW</span>
              <h2>失物 / 招领内容审核</h2>
            </div>
            <span class="count-pill">{{ itemReviews.length }}</span>
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
                <td><span class="status-badge">{{ itemStatusLabel(record) }}</span></td>
                <td>{{ record.reportCount }}</td>
                <td>
                  <div class="row-actions">
                    <button type="button" class="approve" @click="approveContent(record.itemName)">通过</button>
                    <button type="button" class="reject" @click="rejectContent(record.itemName)">关闭</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>

          <div class="record-list">
            <article v-for="record in itemReviews" :key="record.id">
              <div class="mobile-record-title">
                <strong>{{ record.itemName }}</strong>
                <span class="status-badge">{{ bizTypeLabel(record.bizType) }}</span>
              </div>
              <p>{{ categoryLabels[record.category] }} · {{ record.location }}</p>
              <p>{{ itemStatusLabel(record) }} · 举报 {{ record.reportCount }}</p>
              <div class="row-actions">
                <button type="button" class="approve" @click="approveContent(record.itemName)">通过</button>
                <button type="button" class="reject" @click="rejectContent(record.itemName)">关闭</button>
              </div>
            </article>
          </div>
        </section>

        <section v-else-if="navigation.activePage === 'reports'" class="page-stack">
          <div class="action-strip single">
            <label>
              <span>有效举报处理结果</span>
              <input v-model="reportResult" />
            </label>
          </div>

          <div class="report-grid">
            <article v-for="record in reports" :key="record.id" class="report-panel">
              <div class="panel-heading">
                <div>
                  <span class="eyebrow">{{ record.targetType }}</span>
                  <h2>{{ record.reason }}</h2>
                </div>
                <span class="status-badge warn">{{ reportStatusLabels[record.handleStatus] }}</span>
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
                <button type="button" class="approve" @click="handleReport(record.reason, true)">有效</button>
                <button type="button" class="reject" @click="handleReport(record.reason, false)">无效</button>
              </div>
            </article>
          </div>
        </section>

        <section v-else-if="navigation.activePage === 'announcements'" class="page-stack">
          <form class="announcement-form" @submit.prevent="submitAnnouncement">
            <label>
              <span>公告标题</span>
              <input v-model="announcement.title" required maxlength="100" />
            </label>
            <label>
              <span>公告内容</span>
              <textarea v-model="announcement.content" required maxlength="5000" rows="10" />
            </label>
            <label class="check-row">
              <input v-model="announcement.publishNow" type="checkbox" />
              <span>立即发布</span>
            </label>
            <button class="primary-action" type="submit">
              <Megaphone :size="18" />发布公告
            </button>
          </form>
        </section>

        <section v-else class="page-stack">
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
                <td><span class="status-badge">{{ userStatusLabels[record.status] }}</span></td>
                <td>{{ record.lastActiveAt ?? record.createdAt ?? '暂无记录' }}</td>
                <td>
                  <button type="button" class="reject" @click="actionNote = `已准备更新 ${record.nickname} 的 status`">更新状态</button>
                </td>
              </tr>
            </tbody>
          </table>

          <div class="record-list">
            <article v-for="record in filteredUsers" :key="record.id">
              <div class="mobile-record-title">
                <strong>{{ record.nickname }}</strong>
                <span class="status-badge">{{ userStatusLabels[record.status] }}</span>
              </div>
              <p>{{ record.phone }} · {{ userRoleLabels[record.role] }}</p>
              <p>{{ certStatusLabels[record.certStatus] }} · {{ record.creditScore }} 分</p>
              <button type="button" class="reject" @click="actionNote = `已准备更新 ${record.nickname} 的 status`">更新状态</button>
            </article>
          </div>
        </section>

        <p v-if="actionNote" class="action-note"><BarChart3 :size="18" />{{ actionNote }}</p>
      </main>
    </div>
    </template>
    </div>
</template>
