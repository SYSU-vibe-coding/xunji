<script setup lang="ts">
import { computed, onMounted, reactive, ref, type Component } from 'vue';
import {
  ArrowLeft,
  ArrowRight,
  Bell,
  Building2,
  CheckCircle2,
  ChevronRight,
  CircleCheck,
  ClipboardList,
  Home,
  Inbox,
  LockKeyhole,
  MessageSquareText,
  PackageCheck,
  Pencil,
  PlusCircle,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  UserRound,
} from 'lucide-vue-next';

import ItemCard from '@/components/ItemCard.vue';
import {
  ApiError,
  clearStoredToken,
  createFoundItem,
  createLostItem,
  deleteLostItem,
  getLostItem,
  getMyProfile,
  getStoredToken,
  listFoundItems,
  listLostItems,
  listMyClaims,
  listNotifications,
  loginWithPassword,
  registerWithPhone,
  sendSmsCode,
  updateLostItem,
} from '@/api/client';
import { useNavigationStore, type UserPage } from '@/stores/navigation';
import {
  categoryOptions,
  categoryLabels,
  claimStatusLabels,
  contactOptions,
  custodyOptions,
  formatPercent,
  lostStatusLabels,
  noticeTypeLabels,
  reviewStatusLabels,
  scoreTone,
  timeShort,
  verifyLevelLabels,
  type ClaimSummary,
  type ContactPreference,
  type CurrentUser,
  type CustodyType,
  type FoundItemSummary,
  type ItemCategory,
  type LostItemSummary,
  type MatchSummary,
  type NotificationSummary,
} from '@xunji/shared';

const navigation = useNavigationStore();
const authMode = ref<'login' | 'register'>('login');

const navItems: Array<{ key: UserPage; label: string; icon: Component }> = [
  { key: 'home', label: '首页', icon: Home },
  { key: 'search', label: '检索', icon: Search },
  { key: 'publish', label: '发布', icon: PlusCircle },
  { key: 'matches', label: '认领', icon: ClipboardList },
  { key: 'messages', label: '消息', icon: Bell },
  { key: 'profile', label: '我的', icon: UserRound },
];

const mobileNavItems = computed(() => navItems.slice(0, 5));
const showMobileDockIndicator = computed(() => mobileNavItems.value.some((item) => item.key === navigation.activePage));
const activeMobileTabIndex = computed(() => {
  const index = mobileNavItems.value.findIndex((item) => item.key === navigation.activePage);
  return index >= 0 ? index : 0;
});
const mobileDockIndicatorStyle = computed(() => ({
  width: `calc((100% - 16px - ${(mobileNavItems.value.length - 1) * 4}px) / ${mobileNavItems.value.length})`,
  transform: `translateX(calc(${activeMobileTabIndex.value} * (100% + 4px)))`,
}));

const searchMode = ref<'FOUND' | 'LOST'>('FOUND');
const searchQuery = ref('');
const categoryFilter = ref<ItemCategory | 'ALL'>('ALL');
const publishMode = ref<'LOST' | 'FOUND'>('LOST');
const submitState = ref('');
const loadState = ref('');
const currentUser = ref<CurrentUser>(createEmptyUser());
const foundItems = ref<FoundItemSummary[]>([]);
const lostItems = ref<LostItemSummary[]>([]);
const matches = ref<MatchSummary[]>([]);
const claims = ref<ClaimSummary[]>([]);
const notifications = ref<NotificationSummary[]>([]);
const isAuthenticated = ref(Boolean(getStoredToken()));
const authError = ref('');
const smsHint = ref('');
const isSendingCode = ref(false);
const isLoggingIn = ref(false);
const isSubmittingPublish = ref(false);
const selectedLostItem = ref<LostItemSummary | null>(null);
const lostDetailBackPage = ref<UserPage>('profile');
const isEditingLost = ref(false);
const isSavingLost = ref(false);
const toast = ref<{ message: string; tone: 'success' | 'danger' | 'info' } | null>(null);
let toastTimer: number | undefined;

const loginForm = reactive({
  phone: '',
  password: '',
});

const registerForm = reactive({
  phone: '',
  code: '',
  nickname: '',
  password: '',
});

const lostForm = reactive({
  itemName: '',
  category: 'ELECTRONIC' as ItemCategory,
  lostTimeStart: '2026-04-28 09:00:00',
  lostTimeEnd: '2026-04-28 10:00:00',
  lostLocation: '',
  description: '',
  subscribeMatch: true,
  imageUrls: '',
});

const editLostForm = reactive({
  itemName: '',
  category: 'ELECTRONIC' as ItemCategory,
  lostTimeStart: '',
  lostTimeEnd: '',
  lostLocation: '',
  description: '',
  subscribeMatch: true,
  imageUrls: '',
});

const foundForm = reactive({
  itemName: '',
  category: 'CERT' as ItemCategory,
  foundTime: '2026-04-28 12:00:00',
  foundLocation: '',
  custodyType: 'SECURITY' as CustodyType,
  contactPreference: 'IN_APP' as ContactPreference,
  description: '',
  verifyQuestion: '',
  answerKeywords: '',
  imageUrls: '',
});

const unreadCount = computed(() => notifications.value.filter((notice) => !notice.isRead).length);
const topMatch = computed(() => matches.value[0] ?? null);
const featuredFoundItem = computed(() => foundItems.value[0] ?? null);
const activeFoundCount = computed(() => foundItems.value.filter((item) => item.status === 'PENDING').length);
const loginPhoneIsValid = computed(() => /^1\d{10}$/.test(loginForm.phone));
const registerPhoneIsValid = computed(() => /^1\d{10}$/.test(registerForm.phone));
const canLogin = computed(() => loginPhoneIsValid.value && loginForm.password.length >= 6 && !isLoggingIn.value);
const canRegister = computed(
  () =>
    registerPhoneIsValid.value &&
    /^\d{6}$/.test(registerForm.code) &&
    registerForm.password.length >= 6 &&
    registerForm.nickname.trim().length >= 2 &&
    !isLoggingIn.value,
);
const canSubmitLost = computed(
  () => Boolean(lostForm.itemName.trim() && lostForm.lostLocation.trim() && lostForm.lostTimeStart && lostForm.lostTimeEnd) && !isSubmittingPublish.value,
);
const canSaveLost = computed(
  () =>
    Boolean(editLostForm.itemName.trim() && editLostForm.lostLocation.trim() && editLostForm.lostTimeStart && editLostForm.lostTimeEnd) &&
    !isSavingLost.value,
);
const canSubmitFound = computed(
  () => Boolean(foundForm.itemName.trim() && foundForm.foundLocation.trim() && foundForm.foundTime) && !isSubmittingPublish.value,
);
const homeStats = computed(() => [
  { label: '待认领招领', value: activeFoundCount.value, suffix: '条' },
  { label: '我的失物', value: lostItems.value.length, suffix: '条' },
  { label: '信誉分', value: currentUser.value.creditScore, suffix: '' },
]);
const canManageSelectedLost = computed(
  () => Boolean(selectedLostItem.value && selectedLostItem.value.userId === currentUser.value.id),
);

const visibleFoundItems = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase();
  return foundItems.value.filter((item) => {
    const matchesCategory = categoryFilter.value === 'ALL' || item.category === categoryFilter.value;
    const matchesKeyword =
      !keyword ||
      item.itemName.toLowerCase().includes(keyword) ||
      (item.description ?? '').toLowerCase().includes(keyword) ||
      item.foundLocation.toLowerCase().includes(keyword);
    return matchesCategory && matchesKeyword;
  });
});

const visibleLostItems = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase();
  return lostItems.value.filter((item) => {
    const matchesCategory = categoryFilter.value === 'ALL' || item.category === categoryFilter.value;
    const matchesKeyword =
      !keyword ||
      item.itemName.toLowerCase().includes(keyword) ||
      (item.description ?? '').toLowerCase().includes(keyword) ||
      item.lostLocation.toLowerCase().includes(keyword);
    return matchesCategory && matchesKeyword;
  });
});

function go(page: UserPage) {
  navigation.go(page);
}

function showToast(message: string, tone: 'success' | 'danger' | 'info' = 'info') {
  toast.value = { message, tone };
  if (toastTimer) {
    window.clearTimeout(toastTimer);
  }
  toastTimer = window.setTimeout(() => {
    toast.value = null;
  }, 2600);
}

function createEmptyUser(): CurrentUser {
  return {
    id: '',
    phone: '',
    nickname: '用户',
    avatarUrl: null,
    role: 'USER',
    certStatus: 'UNVERIFIED',
    campusId: null,
    realName: null,
    creditScore: 100,
    status: 'ACTIVE',
  };
}

function lostPayloadFromForm(form: typeof lostForm | typeof editLostForm) {
  return {
    itemName: form.itemName,
    category: form.category,
    lostTimeStart: form.lostTimeStart,
    lostTimeEnd: form.lostTimeEnd,
    lostLocation: form.lostLocation,
    description: form.description || null,
    subscribeMatch: form.subscribeMatch,
    imageUrls: splitUrls(form.imageUrls),
  };
}

function fillEditLostForm(item: LostItemSummary) {
  editLostForm.itemName = item.itemName;
  editLostForm.category = item.category;
  editLostForm.lostTimeStart = item.lostTimeStart;
  editLostForm.lostTimeEnd = item.lostTimeEnd;
  editLostForm.lostLocation = item.lostLocation;
  editLostForm.description = item.description ?? '';
  editLostForm.subscribeMatch = Boolean(item.subscribeMatch);
  editLostForm.imageUrls = (item.imageUrls ?? []).join(', ');
}

async function openLostDetail(itemId: string, backPage: UserPage = navigation.activePage) {
  try {
    const detail = await getLostItem(itemId);
    selectedLostItem.value = detail;
    lostDetailBackPage.value = backPage === 'lost-detail' ? 'profile' : backPage;
    fillEditLostForm(detail);
    isEditingLost.value = false;
    navigation.go('lost-detail');
  } catch (error) {
    showToast(error instanceof Error ? error.message : '无法打开失物详情', 'danger');
  }
}

async function requestSmsCode() {
  authError.value = '';
  smsHint.value = '';
  if (!registerPhoneIsValid.value) {
    authError.value = '请输入 11 位大陆手机号';
    return;
  }
  isSendingCode.value = true;
  try {
    const data = await sendSmsCode(registerForm.phone);
    if (data.debugCode) {
      registerForm.code = data.debugCode;
    }
    smsHint.value = '验证码已发送';
  } catch (error) {
    authError.value = error instanceof Error ? error.message : '验证码发送失败';
  } finally {
    isSendingCode.value = false;
  }
}

async function submitLogin() {
  authError.value = '';
  if (!canLogin.value) {
    authError.value = '手机号或密码不正确';
    return;
  }
  isLoggingIn.value = true;
  try {
    const data = await loginWithPassword(loginForm.phone, loginForm.password);
    currentUser.value = {
      ...createEmptyUser(),
      id: data.user.id,
      phone: loginForm.phone,
      nickname: data.user.nickname,
      avatarUrl: data.user.avatarUrl,
      role: data.user.role,
      certStatus: data.user.certStatus,
      creditScore: data.user.creditScore,
    };
    isAuthenticated.value = true;
    await loadBackendData();
  } catch (error) {
    authError.value = error instanceof Error ? error.message : '登录失败';
  } finally {
    isLoggingIn.value = false;
  }
}

async function submitRegister() {
  authError.value = '';
  if (!canRegister.value) {
    authError.value = '请完整填写注册信息';
    return;
  }
  isLoggingIn.value = true;
  try {
    const data = await registerWithPhone({
      phone: registerForm.phone,
      code: registerForm.code,
      nickname: registerForm.nickname.trim(),
      password: registerForm.password,
    });
    currentUser.value = {
      ...createEmptyUser(),
      id: data.user.id,
      phone: registerForm.phone,
      nickname: data.user.nickname,
      avatarUrl: data.user.avatarUrl,
      role: data.user.role,
      certStatus: data.user.certStatus,
      creditScore: data.user.creditScore,
    };
    isAuthenticated.value = true;
    await loadBackendData();
  } catch (error) {
    authError.value = error instanceof Error ? error.message : '注册失败';
  } finally {
    isLoggingIn.value = false;
  }
}

function logout() {
  clearStoredToken();
  isAuthenticated.value = false;
  currentUser.value = createEmptyUser();
  selectedLostItem.value = null;
  isEditingLost.value = false;
}

async function loadBackendData() {
  try {
    const [profile, foundPage, lostPage, claimPage, notificationPage] = await Promise.all([
      getMyProfile(),
      listFoundItems(),
      listLostItems(),
      listMyClaims(),
      listNotifications(),
    ]);
    currentUser.value = profile;
    foundItems.value = foundPage.list;
    lostItems.value = lostPage.list;
    matches.value = [];
    claims.value = claimPage.list;
    notifications.value = notificationPage.list;
    loadState.value = `招领 ${foundPage.total} · 失物 ${lostPage.total}`;
  } catch (error) {
    if (error instanceof ApiError && error.code === 40002) {
      clearStoredToken();
      isAuthenticated.value = false;
      currentUser.value = createEmptyUser();
      foundItems.value = [];
      lostItems.value = [];
      matches.value = [];
      claims.value = [];
      notifications.value = [];
      loadState.value = '登录已失效，请重新登录';
      return;
    }
    loadState.value = '服务暂不可用';
    foundItems.value = [];
    lostItems.value = [];
    matches.value = [];
    claims.value = [];
    notifications.value = [];
  }
}

function splitUrls(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

async function submitPublish() {
  submitState.value = '';
  isSubmittingPublish.value = true;
  try {
    if (publishMode.value === 'LOST') {
      const result = await createLostItem(lostPayloadFromForm(lostForm));
      showToast('失物发布成功', 'success');
      await loadBackendData();
      await openLostDetail(result.id, 'profile');
    } else {
      const verifyQuestions =
        foundForm.verifyQuestion && foundForm.answerKeywords
          ? [
              {
                questionText: foundForm.verifyQuestion,
                answerKeywords: foundForm.answerKeywords
                  .split(',')
                  .map((keyword) => keyword.trim())
                  .filter(Boolean),
              },
            ]
          : [];
      await createFoundItem({
        itemName: foundForm.itemName,
        category: foundForm.category,
        foundTime: foundForm.foundTime,
        foundLocation: foundForm.foundLocation,
        custodyType: foundForm.custodyType,
        contactPreference: foundForm.contactPreference,
        description: foundForm.description || null,
        verifyQuestions,
        imageUrls: splitUrls(foundForm.imageUrls),
      });
      showToast('招领发布成功', 'success');
      await loadBackendData();
    }
  } catch (error) {
    showToast(error instanceof Error ? error.message : '提交失败', 'danger');
  } finally {
    isSubmittingPublish.value = false;
  }
}

async function saveLostDetail() {
  if (!selectedLostItem.value || !canSaveLost.value) return;
  const itemId = selectedLostItem.value.id;
  const backPage = lostDetailBackPage.value;
  isSavingLost.value = true;
  try {
    await updateLostItem({
      id: itemId,
      data: lostPayloadFromForm(editLostForm),
    });
    showToast('失物信息已提交审核', 'success');
    await loadBackendData();
    await openLostDetail(itemId, backPage);
  } catch (error) {
    showToast(error instanceof Error ? error.message : '保存失败', 'danger');
  } finally {
    isSavingLost.value = false;
  }
}

async function removeLostDetail() {
  if (!selectedLostItem.value) return;
  if (!window.confirm('确认删除这条失物信息？')) return;
  isSavingLost.value = true;
  try {
    await deleteLostItem(selectedLostItem.value.id);
    showToast('失物信息已删除', 'success');
    selectedLostItem.value = null;
    isEditingLost.value = false;
    await loadBackendData();
    navigation.go('profile');
  } catch (error) {
    showToast(error instanceof Error ? error.message : '删除失败', 'danger');
  } finally {
    isSavingLost.value = false;
  }
}

onMounted(async () => {
  if (isAuthenticated.value) {
    await loadBackendData();
  }
});
</script>

<template>
  <div class="app-frame" :class="{ 'auth-mode': !isAuthenticated }">
    <Transition name="toast">
      <div v-if="toast" class="toast" :class="`toast-${toast.tone}`">
        <CheckCircle2 v-if="toast.tone === 'success'" :size="18" />
        <LockKeyhole v-else-if="toast.tone === 'danger'" :size="18" />
        <Bell v-else :size="18" />
        <span>{{ toast.message }}</span>
      </div>
    </Transition>

    <section v-if="!isAuthenticated" class="auth-view">
      <div class="auth-hero">
        <div class="brand-lockup">
          <span class="brand-mark"><Building2 :size="22" /></span>
          <strong>寻迹</strong>
        </div>
        <div class="auth-copy">
          <span class="eyebrow">Campus Lost & Found</span>
          <h1>寻迹</h1>
          <p>校园失物招领工作台。</p>
        </div>
        <div class="feature-list">
          <span><ShieldCheck :size="16" />实名可信</span>
          <span><Sparkles :size="16" />智能匹配</span>
          <span><CircleCheck :size="16" />闭环交接</span>
        </div>
      </div>

      <form class="auth-card" @submit.prevent="authMode === 'login' ? submitLogin() : submitRegister()">
        <div class="card-header">
          <span class="eyebrow">Account</span>
          <h2>{{ authMode === 'login' ? '登录' : '注册' }}</h2>
        </div>

        <div class="auth-tabs" role="tablist" aria-label="登录注册切换">
          <button type="button" :class="{ active: authMode === 'login' }" @click="authMode = 'login'; authError = ''; smsHint = ''">
            登录
          </button>
          <button type="button" :class="{ active: authMode === 'register' }" @click="authMode = 'register'; authError = ''; smsHint = ''">
            注册
          </button>
        </div>

        <div v-if="authMode === 'login'" class="field-group">
          <label class="field" :data-invalid="loginForm.phone && !loginPhoneIsValid ? 'true' : undefined">
            <span>手机号</span>
            <input v-model="loginForm.phone" inputmode="numeric" maxlength="11" placeholder="13800000010" aria-label="手机号" />
          </label>
          <label class="field">
            <span>密码</span>
            <input v-model="loginForm.password" type="password" autocomplete="current-password" placeholder="至少 6 位" aria-label="密码" />
          </label>
        </div>

        <div v-else class="field-group">
          <label class="field" :data-invalid="registerForm.phone && !registerPhoneIsValid ? 'true' : undefined">
            <span>手机号</span>
            <input v-model="registerForm.phone" inputmode="numeric" maxlength="11" placeholder="13800000010" aria-label="注册手机号" />
          </label>
          <label class="field">
            <span>验证码</span>
            <div class="input-group">
              <input v-model="registerForm.code" inputmode="numeric" maxlength="6" placeholder="123456" aria-label="验证码" />
              <button class="button button-secondary" type="button" :disabled="isSendingCode" @click="requestSmsCode">
                {{ isSendingCode ? '发送中' : '获取' }}
              </button>
            </div>
          </label>
          <label class="field">
            <span>昵称</span>
            <input v-model="registerForm.nickname" maxlength="20" placeholder="张同学" aria-label="昵称" />
          </label>
          <label class="field">
            <span>密码</span>
            <input v-model="registerForm.password" type="password" autocomplete="new-password" placeholder="至少 6 位" aria-label="注册密码" />
          </label>
        </div>

        <p v-if="smsHint" class="alert alert-info"><CheckCircle2 :size="17" />{{ smsHint }}</p>
        <p v-if="authError" class="alert alert-danger"><LockKeyhole :size="17" />{{ authError }}</p>

        <button class="button button-primary button-block" type="submit" :disabled="authMode === 'login' ? !canLogin : !canRegister">
          {{ isLoggingIn ? '处理中' : authMode === 'login' ? '登录' : '注册并登录' }}
          <ArrowRight :size="17" />
        </button>
      </form>
    </section>

    <template v-else>
      <aside class="desktop-sidebar" aria-label="用户端主导航">
        <div class="brand-lockup">
          <span class="brand-mark"><Building2 :size="22" /></span>
          <strong>寻迹</strong>
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

        <button class="profile-chip" type="button" @click="go('profile')">
          <span class="avatar">{{ currentUser.nickname.slice(0, 1) }}</span>
          <span>
            <strong>{{ currentUser.nickname }}</strong>
            <small>{{ currentUser.creditScore }} 信誉分</small>
          </span>
          <ChevronRight :size="17" />
        </button>
      </aside>

      <header class="mobile-topbar">
        <div class="brand-lockup">
          <span class="brand-mark"><Building2 :size="20" /></span>
          <strong>寻迹</strong>
        </div>
        <div class="topbar-actions">
          <button class="icon-button" type="button" aria-label="消息" @click="go('messages')">
            <Bell :size="20" />
            <span v-if="unreadCount" class="dot">{{ unreadCount }}</span>
          </button>
          <button class="avatar-button" type="button" aria-label="我的" @click="go('profile')">
            {{ currentUser.nickname.slice(0, 1) }}
          </button>
        </div>
      </header>

      <main class="content-shell">
        <Transition name="page-transition" mode="out-in">
          <section v-if="navigation.activePage === 'home'" key="home" class="page-stack">
            <article class="hero-panel">
              <div class="hero-copy">
                <span class="eyebrow">Xunji</span>
                <h1>你好，{{ currentUser.nickname }}</h1>
                <p v-if="loadState">{{ loadState }}</p>
              </div>
              <button type="button" class="button button-primary" @click="go('publish')">
                <PlusCircle :size="18" />
                发布信息
              </button>
            </article>

            <div class="stat-grid">
              <article v-for="stat in homeStats" :key="stat.label" class="stat-card">
                <span>{{ stat.label }}</span>
                <strong>{{ stat.value }}{{ stat.suffix }}</strong>
              </article>
            </div>

            <div class="quick-grid">
              <button type="button" class="command-card" @click="publishMode = 'LOST'; go('publish')">
                <span class="command-icon"><Search :size="22" /></span>
                <span>
                  <strong>我丢了东西</strong>
                  <small>发布失物并订阅匹配</small>
                </span>
                <ChevronRight :size="18" />
              </button>
              <button type="button" class="command-card accent" @click="publishMode = 'FOUND'; go('publish')">
                <span class="command-icon"><PackageCheck :size="22" /></span>
                <span>
                  <strong>我捡到东西</strong>
                  <small>登记招领与验证问题</small>
                </span>
                <ChevronRight :size="18" />
              </button>
            </div>

            <div class="dashboard-grid">
              <article class="card match-card">
                <div class="card-header horizontal">
                  <div>
                    <span class="eyebrow">AI Match</span>
                    <h2>高匹配线索</h2>
                  </div>
                  <span v-if="topMatch" class="badge badge-success">{{ formatPercent(topMatch.totalScore) }}</span>
                </div>
                <div v-if="topMatch && featuredFoundItem" class="match-preview">
                  <div class="inline-item">
                    <img v-if="featuredFoundItem.coverImageUrl" :src="featuredFoundItem.coverImageUrl" :alt="featuredFoundItem.itemName" />
                    <div v-else class="inline-item-fallback"><ShieldCheck :size="24" /></div>
                    <div>
                      <strong>{{ featuredFoundItem.itemName }}</strong>
                      <span>{{ categoryLabels[featuredFoundItem.category] }} · {{ featuredFoundItem.foundLocation }}</span>
                    </div>
                  </div>
                  <div class="score-stack">
                    <div class="score-row">
                      <span>图像</span>
                      <strong>{{ topMatch.imageScore }}</strong>
                    </div>
                    <div class="score-row">
                      <span>文本</span>
                      <strong>{{ topMatch.textScore }}</strong>
                    </div>
                    <div class="score-row">
                      <span>地点</span>
                      <strong>{{ topMatch.locationScore }}</strong>
                    </div>
                    <div class="progress-track">
                      <span :style="{ width: `${topMatch.totalScore}%` }"></span>
                    </div>
                  </div>
                </div>
                <div v-else class="empty-state compact">
                  <Sparkles :size="22" />
                  <strong>暂无匹配线索</strong>
                </div>
              </article>

              <article class="card">
                <div class="card-header horizontal">
                  <div>
                    <span class="eyebrow">Today</span>
                    <h2>处理提醒</h2>
                  </div>
                  <span class="badge">{{ unreadCount }} 未读</span>
                </div>
                <div class="timeline-list">
                  <div v-for="notice in notifications.slice(0, 3)" :key="notice.id" class="timeline-row">
                    <span :class="{ unread: !notice.isRead }"></span>
                    <div>
                      <strong>{{ notice.title }}</strong>
                      <small>{{ noticeTypeLabels[notice.noticeType] }} · {{ timeShort(notice.createdAt) }}</small>
                    </div>
                  </div>
                  <div v-if="!notifications.length" class="empty-state compact">
                    <Bell :size="22" />
                    <strong>暂无消息</strong>
                  </div>
                </div>
              </article>
            </div>

            <div class="section-heading">
              <div>
                <span class="eyebrow">Latest Found</span>
                <h2>最新招领</h2>
              </div>
              <button type="button" class="button button-ghost" @click="go('search')">查看全部</button>
            </div>

            <div class="item-grid">
              <ItemCard v-for="item in foundItems.slice(0, 4)" :key="item.id" kind="found" :item="item" />
            </div>
            <div v-if="!foundItems.length" class="empty-state">
              <PackageCheck :size="24" />
              <strong>暂无招领信息</strong>
            </div>
          </section>

          <section v-else-if="navigation.activePage === 'search'" key="search" class="page-stack">
            <div class="page-heading">
              <span class="eyebrow">Search</span>
              <h1>检索校园物品</h1>
            </div>

            <article class="card toolbar-card">
              <div class="tabs" role="tablist" aria-label="检索类型">
                <button type="button" :class="{ active: searchMode === 'FOUND' }" @click="searchMode = 'FOUND'">招领</button>
                <button type="button" :class="{ active: searchMode === 'LOST' }" @click="searchMode = 'LOST'">失物</button>
              </div>
              <label class="search-field">
                <Search :size="18" />
                <input v-model="searchQuery" type="search" placeholder="物品名称、地点、描述" />
              </label>
              <div class="chip-row" aria-label="类别筛选">
                <button type="button" :class="{ active: categoryFilter === 'ALL' }" @click="categoryFilter = 'ALL'">全部</button>
                <button
                  v-for="option in categoryOptions"
                  :key="option.value"
                  type="button"
                  :class="{ active: categoryFilter === option.value }"
                  @click="categoryFilter = option.value"
                >
                  {{ option.label }}
                </button>
              </div>
            </article>

            <div class="item-grid">
              <template v-if="searchMode === 'FOUND'">
                <ItemCard v-for="item in visibleFoundItems" :key="item.id" kind="found" :item="item" />
              </template>
              <template v-else>
                <ItemCard v-for="item in visibleLostItems" :key="item.id" kind="lost" :item="item" interactive @open="openLostDetail(item.id, 'search')" />
              </template>
            </div>
            <div
              v-if="(searchMode === 'FOUND' && !visibleFoundItems.length) || (searchMode === 'LOST' && !visibleLostItems.length)"
              class="empty-state"
            >
              <SlidersHorizontal :size="24" />
              <strong>没有符合条件的记录</strong>
            </div>
          </section>

          <section v-else-if="navigation.activePage === 'publish'" key="publish" class="page-stack">
            <div class="page-heading with-actions">
              <div>
                <span class="eyebrow">Publish</span>
                <h1>发布信息</h1>
              </div>
              <div class="tabs compact" role="tablist" aria-label="发布类型">
                <button type="button" :class="{ active: publishMode === 'LOST' }" @click="publishMode = 'LOST'">失物</button>
                <button type="button" :class="{ active: publishMode === 'FOUND' }" @click="publishMode = 'FOUND'">招领</button>
              </div>
            </div>

            <form v-if="publishMode === 'LOST'" class="card form-card" @submit.prevent="submitPublish">
              <div class="card-header">
                <h2>失物信息</h2>
              </div>
              <div class="field-grid">
                <label class="field">
                  <span>物品名称</span>
                  <input v-model="lostForm.itemName" required maxlength="100" placeholder="白色 AirPods Pro" />
                </label>
                <label class="field">
                  <span>物品类别</span>
                  <select v-model="lostForm.category">
                    <option v-for="option in categoryOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                </label>
                <label class="field">
                  <span>丢失开始时间</span>
                  <input v-model="lostForm.lostTimeStart" required />
                </label>
                <label class="field">
                  <span>丢失结束时间</span>
                  <input v-model="lostForm.lostTimeEnd" required />
                </label>
                <label class="field span-2">
                  <span>丢失地点</span>
                  <input v-model="lostForm.lostLocation" required maxlength="100" placeholder="图书馆二楼东侧自习区" />
                </label>
                <label class="field span-2">
                  <span>物品描述</span>
                  <textarea v-model="lostForm.description" maxlength="500" rows="4" placeholder="颜色、品牌、特殊标记" />
                </label>
                <label class="field span-2">
                  <span>图片地址</span>
                  <input v-model="lostForm.imageUrls" placeholder="上传接口返回 URL，多个用逗号分隔" />
                </label>
                <label class="switch-row span-2">
                  <input v-model="lostForm.subscribeMatch" type="checkbox" />
                  <span>
                    <strong>订阅匹配提醒</strong>
                  </span>
                </label>
              </div>
              <button class="button button-primary button-block" type="submit" :disabled="!canSubmitLost">
                {{ isSubmittingPublish ? '提交中' : '提交失物' }}
              </button>
            </form>

            <form v-else class="card form-card" @submit.prevent="submitPublish">
              <div class="card-header">
                <h2>招领信息</h2>
              </div>
              <div class="field-grid">
                <label class="field">
                  <span>物品名称</span>
                  <input v-model="foundForm.itemName" required maxlength="100" placeholder="校园一卡通" />
                </label>
                <label class="field">
                  <span>物品类别</span>
                  <select v-model="foundForm.category">
                    <option v-for="option in categoryOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                </label>
                <label class="field">
                  <span>拾获时间</span>
                  <input v-model="foundForm.foundTime" required />
                </label>
                <label class="field">
                  <span>拾获地点</span>
                  <input v-model="foundForm.foundLocation" required maxlength="100" placeholder="南区食堂二楼" />
                </label>
                <label class="field">
                  <span>保管方式</span>
                  <select v-model="foundForm.custodyType">
                    <option v-for="option in custodyOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                </label>
                <label class="field">
                  <span>联系方式偏好</span>
                  <select v-model="foundForm.contactPreference">
                    <option v-for="option in contactOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                </label>
                <label class="field span-2">
                  <span>验证问题</span>
                  <input v-model="foundForm.verifyQuestion" maxlength="100" placeholder="请说出物品上的特殊标记" />
                </label>
                <label class="field span-2">
                  <span>答案关键词</span>
                  <input v-model="foundForm.answerKeywords" placeholder="关键词用逗号分隔" />
                </label>
                <label class="field span-2">
                  <span>公开描述</span>
                  <textarea v-model="foundForm.description" maxlength="500" rows="4" placeholder="发现位置、保管方式、可公开线索" />
                </label>
              </div>
              <button class="button button-primary button-block" type="submit" :disabled="!canSubmitFound">
                {{ isSubmittingPublish ? '提交中' : '提交招领' }}
              </button>
            </form>

            <p v-if="submitState" class="alert alert-info"><CheckCircle2 :size="18" />{{ submitState }}</p>
          </section>

          <section v-else-if="navigation.activePage === 'matches'" key="matches" class="page-stack">
            <div class="page-heading">
              <span class="eyebrow">Claims</span>
              <h1>匹配与认领</h1>
            </div>

            <div class="match-list">
              <article v-for="match in matches" :key="match.matchId" class="card claim-row" :class="scoreTone(match.totalScore)">
                <div>
                  <span class="eyebrow">{{ match.matchStatus }}</span>
                  <h2>{{ match.counterpart.itemName }}</h2>
                  <p>{{ match.counterpart.location }} · {{ timeShort(match.counterpart.time) }}</p>
                </div>
                <div class="claim-score">
                  <strong>{{ formatPercent(match.totalScore) }}</strong>
                  <span>综合匹配</span>
                </div>
                <button class="button button-secondary" type="button" :disabled="!match.canClaim">发起认领</button>
              </article>
            </div>
            <div v-if="!matches.length" class="empty-state">
              <ClipboardList :size="24" />
              <strong>暂无匹配与认领</strong>
            </div>

            <div class="claim-grid">
              <article v-for="claim in claims" :key="claim.id" class="card mini-card">
                <span class="badge">{{ claimStatusLabels[claim.reviewStatus] }}</span>
                <h2>{{ claim.itemName }}</h2>
                <p>{{ verifyLevelLabels[claim.verifyLevel] }}</p>
                <small>{{ claim.handoverLocation ?? '未安排交接' }}</small>
              </article>
            </div>
          </section>

          <section v-else-if="navigation.activePage === 'messages'" key="messages" class="page-stack">
            <div class="page-heading with-actions">
              <div>
                <span class="eyebrow">Notifications</span>
                <h1>消息中心</h1>
              </div>
              <span class="badge badge-success">{{ unreadCount }} 未读</span>
            </div>

            <div class="message-list">
              <article v-for="notice in notifications" :key="notice.id" class="card message-row" :class="{ unread: !notice.isRead }">
                <span class="message-icon"><MessageSquareText :size="22" /></span>
                <div>
                  <span>{{ noticeTypeLabels[notice.noticeType] }} · {{ notice.createdAt }}</span>
                  <h2>{{ notice.title }}</h2>
                  <p>{{ notice.content }}</p>
                </div>
              </article>
            </div>
            <div v-if="!notifications.length" class="empty-state">
              <MessageSquareText :size="24" />
              <strong>暂无消息</strong>
            </div>
          </section>

          <section v-else-if="navigation.activePage === 'lost-detail'" key="lost-detail" class="page-stack">
            <div class="page-heading with-actions">
              <div>
                <span class="eyebrow">Lost Item</span>
                <h1>{{ selectedLostItem?.itemName ?? '失物详情' }}</h1>
              </div>
              <button type="button" class="button button-secondary" @click="go(lostDetailBackPage)">
                <ArrowLeft :size="18" />
                返回
              </button>
            </div>

            <article v-if="selectedLostItem" class="card detail-card">
              <div class="detail-hero">
                <div class="detail-media">
                  <img v-if="selectedLostItem.coverImageUrl" :src="selectedLostItem.coverImageUrl" :alt="selectedLostItem.itemName" />
                  <div v-else class="inline-item-fallback"><Inbox :size="32" /></div>
                </div>
                <div class="detail-summary">
                  <div class="detail-badges">
                    <span class="badge">{{ categoryLabels[selectedLostItem.category] }}</span>
                    <span class="badge">{{ lostStatusLabels[selectedLostItem.status] }}</span>
                    <span class="badge">{{ reviewStatusLabels[selectedLostItem.reviewStatus] }}</span>
                  </div>
                  <h2>{{ selectedLostItem.itemName }}</h2>
                  <p>{{ selectedLostItem.description || '无描述' }}</p>
                  <dl class="detail-list">
                    <div>
                      <dt>丢失地点</dt>
                      <dd>{{ selectedLostItem.lostLocation }}</dd>
                    </div>
                    <div>
                      <dt>丢失时间</dt>
                      <dd>{{ selectedLostItem.lostTimeStart }} - {{ selectedLostItem.lostTimeEnd }}</dd>
                    </div>
                    <div>
                      <dt>更新时间</dt>
                      <dd>{{ selectedLostItem.updatedAt ?? selectedLostItem.createdAt }}</dd>
                    </div>
                  </dl>
                  <div v-if="canManageSelectedLost" class="row-actions">
                    <button type="button" class="button button-secondary" @click="isEditingLost = !isEditingLost">
                      <Pencil :size="16" />{{ isEditingLost ? '取消编辑' : '编辑' }}
                    </button>
                    <button type="button" class="button button-danger" :disabled="isSavingLost" @click="removeLostDetail">
                      <Trash2 :size="16" />删除
                    </button>
                  </div>
                </div>
              </div>
            </article>

            <form v-if="selectedLostItem && isEditingLost" class="card form-card" @submit.prevent="saveLostDetail">
              <div class="card-header">
                <h2>编辑失物</h2>
              </div>
              <div class="field-grid">
                <label class="field">
                  <span>物品名称</span>
                  <input v-model="editLostForm.itemName" required maxlength="100" />
                </label>
                <label class="field">
                  <span>物品类别</span>
                  <select v-model="editLostForm.category">
                    <option v-for="option in categoryOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                </label>
                <label class="field">
                  <span>丢失开始时间</span>
                  <input v-model="editLostForm.lostTimeStart" required />
                </label>
                <label class="field">
                  <span>丢失结束时间</span>
                  <input v-model="editLostForm.lostTimeEnd" required />
                </label>
                <label class="field span-2">
                  <span>丢失地点</span>
                  <input v-model="editLostForm.lostLocation" required maxlength="100" />
                </label>
                <label class="field span-2">
                  <span>物品描述</span>
                  <textarea v-model="editLostForm.description" maxlength="500" rows="4" />
                </label>
                <label class="field span-2">
                  <span>图片地址</span>
                  <input v-model="editLostForm.imageUrls" />
                </label>
                <label class="switch-row span-2">
                  <input v-model="editLostForm.subscribeMatch" type="checkbox" />
                  <span><strong>订阅匹配提醒</strong></span>
                </label>
              </div>
              <button class="button button-primary button-block" type="submit" :disabled="!canSaveLost">
                {{ isSavingLost ? '保存中' : '保存修改' }}
              </button>
            </form>
          </section>

          <section v-else key="profile" class="page-stack">
            <div class="profile-grid">
              <article class="card profile-card">
                <span class="avatar xl">{{ currentUser.nickname.slice(0, 1) }}</span>
                <div>
                  <span class="eyebrow">Profile</span>
                  <h1>{{ currentUser.nickname }}</h1>
                  <p>{{ currentUser.phone }} · {{ currentUser.campusId ?? '未认证校园编号' }}</p>
                </div>
                <span class="badge badge-success"><ShieldCheck :size="15" />已实名认证</span>
                <button type="button" class="button button-secondary" @click="logout">退出登录</button>
              </article>

              <div class="profile-stats">
                <article class="card stat-card">
                  <Sparkles :size="22" />
                  <strong>{{ currentUser.creditScore }}</strong>
                  <span>信誉分</span>
                </article>
                <article class="card stat-card">
                  <Inbox :size="22" />
                  <strong>{{ lostItems.length }}</strong>
                  <span>我的发布</span>
                </article>
                <article class="card stat-card">
                  <PackageCheck :size="22" />
                  <strong>{{ claims.length }}</strong>
                  <span>我的认领</span>
                </article>
              </div>
            </div>

            <div class="section-heading">
              <div>
                <span class="eyebrow">Mine</span>
                <h2>我的失物</h2>
              </div>
            </div>
            <div class="item-grid">
              <ItemCard v-for="item in lostItems" :key="item.id" kind="lost" :item="item" interactive @open="openLostDetail(item.id, 'profile')" />
            </div>
            <div v-if="!lostItems.length" class="empty-state">
              <Inbox :size="24" />
              <strong>暂无我的失物</strong>
            </div>
          </section>
        </Transition>
      </main>

      <nav class="mobile-dock" aria-label="移动端主导航">
        <span v-if="showMobileDockIndicator" class="dock-indicator" :style="mobileDockIndicatorStyle"></span>
        <button
          v-for="item in mobileNavItems"
          :key="item.key"
          type="button"
          :class="{ active: navigation.activePage === item.key }"
          :aria-current="navigation.activePage === item.key ? 'page' : undefined"
          @click="go(item.key)"
        >
          <component :is="item.icon" :size="20" />
          <span>{{ item.label }}</span>
        </button>
      </nav>
    </template>
  </div>
</template>
