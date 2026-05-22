<script setup lang="ts">
import { computed, onMounted, reactive, ref, type Component } from 'vue';
import {
  Bell,
  Building2,
  CheckCircle2,
  ClipboardList,
  Home,
  Inbox,
  MessageSquareText,
  PackageCheck,
  PlusCircle,
  Search,
  ShieldCheck,
  Sparkles,
  UserRound,
} from 'lucide-vue-next';

import ItemCard from '@/components/ItemCard.vue';
import {
  clearStoredToken,
  createFoundItem,
  createLostItem,
  getMyProfile,
  getStoredToken,
  listFoundItems,
  listLostItems,
  loginWithPhoneCode,
  sendSmsCode,
} from '@/api/client';
import { useNavigationStore, type UserPage } from '@/stores/navigation';
import {
  categoryOptions,
  claimStatusLabels,
  contactOptions,
  custodyOptions,
  demoClaims,
  demoFoundItems,
  demoLostItems,
  demoMatches,
  demoNotifications,
  demoUser,
  formatPercent,
  noticeTypeLabels,
  scoreTone,
  timeShort,
  verifyLevelLabels,
  type ContactPreference,
  type CustodyType,
  type ItemCategory,
} from '@xunji/shared';

const navigation = useNavigationStore();

const navItems: Array<{ key: UserPage; label: string; icon: Component }> = [
  { key: 'home', label: '首页', icon: Home },
  { key: 'search', label: '搜索', icon: Search },
  { key: 'publish', label: '发布', icon: PlusCircle },
  { key: 'matches', label: '匹配', icon: ClipboardList },
  { key: 'messages', label: '消息', icon: Bell },
  { key: 'profile', label: '我的', icon: UserRound },
];

const searchMode = ref<'FOUND' | 'LOST'>('FOUND');
const searchQuery = ref('');
const categoryFilter = ref<ItemCategory | 'ALL'>('ALL');
const publishMode = ref<'LOST' | 'FOUND'>('LOST');
const submitState = ref('');
const loadState = ref('后端未连接时自动使用演示数据');
const currentUser = ref(demoUser);
const foundItems = ref(demoFoundItems);
const lostItems = ref(demoLostItems);
const isAuthenticated = ref(Boolean(getStoredToken()));
const authError = ref('');
const smsHint = ref('');

const loginForm = reactive({
  phone: '13800000010',
  code: '123456',
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

const unreadCount = computed(() => demoNotifications.filter((notice) => !notice.isRead).length);
const topMatch = computed(() => demoMatches[0]);
const activeFoundCount = computed(() => foundItems.value.filter((item) => item.status === 'PENDING').length);

const visibleFoundItems = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase();
  return foundItems.value.filter((item) => {
    const matchesCategory = categoryFilter.value === 'ALL' || item.category === categoryFilter.value;
    const matchesKeyword =
      !keyword ||
      item.itemName.toLowerCase().includes(keyword) ||
      item.description.toLowerCase().includes(keyword) ||
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
      item.description.toLowerCase().includes(keyword) ||
      item.lostLocation.toLowerCase().includes(keyword);
    return matchesCategory && matchesKeyword;
  });
});

function go(page: UserPage) {
  navigation.go(page);
}

async function requestSmsCode() {
  authError.value = '';
  try {
    const data = await sendSmsCode(loginForm.phone);
    smsHint.value = `验证码已发送，演示码：${data.debugCode ?? loginForm.code}`;
  } catch (error) {
    authError.value = error instanceof Error ? error.message : '验证码发送失败';
  }
}

async function submitLogin() {
  authError.value = '';
  try {
    const data = await loginWithPhoneCode(loginForm.phone, loginForm.code);
    currentUser.value = {
      ...demoUser,
      id: data.user.id,
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
  }
}

function logout() {
  clearStoredToken();
  isAuthenticated.value = false;
  currentUser.value = demoUser;
}

async function loadBackendData() {
  try {
    const [profile, foundPage, lostPage] = await Promise.all([
      getMyProfile(),
      listFoundItems(),
      listLostItems(),
    ]);
    currentUser.value = profile;
    foundItems.value = foundPage.list.length ? foundPage.list : demoFoundItems;
    lostItems.value = lostPage.list.length ? lostPage.list : demoLostItems;
    loadState.value = `已连接后端：招领 ${foundPage.total} 条，失物 ${lostPage.total} 条`;
  } catch (error) {
    loadState.value = error instanceof Error ? `后端数据加载失败，使用演示数据：${error.message}` : '使用演示数据';
    foundItems.value = demoFoundItems;
    lostItems.value = demoLostItems;
  }
}

function splitUrls(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

async function submitPublish() {
  submitState.value = '提交中...';
  try {
    if (publishMode.value === 'LOST') {
      const result = await createLostItem({
        itemName: lostForm.itemName,
        category: lostForm.category,
        lostTimeStart: lostForm.lostTimeStart,
        lostTimeEnd: lostForm.lostTimeEnd,
        lostLocation: lostForm.lostLocation,
        description: lostForm.description || null,
        subscribeMatch: lostForm.subscribeMatch,
        imageUrls: splitUrls(lostForm.imageUrls),
      });
      submitState.value = `失物发布成功，状态：${result.status}`;
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
      const result = await createFoundItem({
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
      submitState.value = `招领发布成功，状态：${result.status}${result.isSensitive ? '，已按敏感物品处理' : ''}`;
    }
    await loadBackendData();
  } catch (error) {
    submitState.value = error instanceof Error ? `提交失败：${error.message}` : '提交失败';
  }
}

onMounted(async () => {
  if (isAuthenticated.value) {
    await loadBackendData();
  }
});
</script>

<template>
  <div class="app-frame" :class="{ 'login-mode': !isAuthenticated }">
    <section v-if="!isAuthenticated" class="login-screen">
      <div class="login-visual">
        <div class="brand-lockup">
          <span class="brand-mark"><Building2 :size="22" /></span>
          <strong>寻迹</strong>
        </div>
        <h1>校园失物招领，从真实身份开始</h1>
        <p>登录后可发布失物、登记招领、查看匹配结果和交接提醒。</p>
        <div class="login-bullets">
          <span><ShieldCheck :size="17" />敏感证件脱敏展示</span>
          <span><Sparkles :size="17" />AI 匹配推荐</span>
          <span><CheckCircle2 :size="17" />交接后同步积分</span>
        </div>
      </div>

      <form class="login-card" @submit.prevent="submitLogin">
        <span class="eyebrow">USER SIGN IN</span>
        <h2>用户端登录</h2>
        <label>
          <span>手机号</span>
          <input v-model="loginForm.phone" inputmode="numeric" maxlength="11" placeholder="请输入 11 位手机号" />
        </label>
        <label>
          <span>短信验证码</span>
          <div class="code-row">
            <input v-model="loginForm.code" inputmode="numeric" maxlength="6" placeholder="123456" />
            <button type="button" class="secondary-action" @click="requestSmsCode">获取验证码</button>
          </div>
        </label>
        <p v-if="smsHint" class="form-hint">{{ smsHint }}</p>
        <p v-if="authError" class="form-error">{{ authError }}</p>
        <button class="primary-action" type="submit">登录用户端</button>
      </form>
    </section>

    <template v-else>
    <aside class="desktop-rail" aria-label="用户端主导航">
      <div class="brand-lockup">
        <span class="brand-mark"><Building2 :size="22" /></span>
        <strong>寻迹</strong>
      </div>

      <nav class="rail-nav">
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

      <div class="rail-user">
        <span class="avatar">{{ currentUser.nickname.slice(0, 1) }}</span>
        <div>
          <strong>{{ currentUser.nickname }}</strong>
          <span>{{ currentUser.creditScore }} 信誉分</span>
        </div>
      </div>
    </aside>

    <div class="mobile-topbar">
      <div class="brand-lockup">
        <span class="brand-mark"><Building2 :size="20" /></span>
        <strong>寻迹</strong>
      </div>
      <button class="icon-button" type="button" aria-label="消息" @click="go('messages')">
        <Bell :size="20" />
        <span v-if="unreadCount" class="dot">{{ unreadCount }}</span>
      </button>
    </div>

    <main class="content-shell">
      <section v-if="navigation.activePage === 'home'" class="page-stack">
        <div class="hero-strip">
          <div>
            <span class="eyebrow">CAMPUS LOST & FOUND</span>
            <h1>你好，{{ currentUser.nickname }}</h1>
            <p>{{ loadState }} · {{ currentUser.creditScore }} 信誉分 · {{ activeFoundCount }} 条待认领招领</p>
          </div>
          <button type="button" class="primary-action" @click="go('publish')">
            <PlusCircle :size="18" />
            发布
          </button>
        </div>

        <div class="home-grid">
          <button type="button" class="quick-action lost" @click="publishMode = 'LOST'; go('publish')">
            <Search :size="26" />
            <span>我丢了东西</span>
            <small>发布寻物信息并订阅匹配</small>
          </button>
          <button type="button" class="quick-action found" @click="publishMode = 'FOUND'; go('publish')">
            <PackageCheck :size="26" />
            <span>我捡到东西</span>
            <small>登记招领与验证问题</small>
          </button>
        </div>

        <article class="match-highlight">
          <div class="section-heading compact">
            <div>
              <span class="eyebrow">NEW MATCH</span>
              <h2>高匹配线索</h2>
            </div>
            <span class="status-badge strong">{{ formatPercent(topMatch.totalScore) }}</span>
          </div>
          <div class="match-body">
            <ItemCard kind="found" :item="foundItems[0] ?? demoFoundItems[0]" compact />
            <div class="score-panel">
              <div class="score-line">
                <span>图像</span>
                <strong>{{ topMatch.imageScore }}</strong>
              </div>
              <div class="score-line">
                <span>文本</span>
                <strong>{{ topMatch.textScore }}</strong>
              </div>
              <div class="score-line">
                <span>地点</span>
                <strong>{{ topMatch.locationScore }}</strong>
              </div>
              <div class="score-track">
                <span :style="{ width: `${topMatch.totalScore}%` }"></span>
              </div>
            </div>
          </div>
        </article>

        <div class="section-heading">
          <div>
            <span class="eyebrow">LATEST FOUND</span>
            <h2>最新招领</h2>
          </div>
          <button type="button" class="text-button" @click="go('search')">查看全部</button>
        </div>

        <div class="item-grid">
          <ItemCard v-for="item in foundItems.slice(0, 4)" :key="item.id" kind="found" :item="item" />
        </div>
      </section>

      <section v-else-if="navigation.activePage === 'search'" class="page-stack">
        <div class="section-heading">
          <div>
            <span class="eyebrow">物品检索</span>
            <h1>物品检索</h1>
          </div>
        </div>

        <div class="search-toolbar">
          <div class="segmented">
            <button type="button" :class="{ active: searchMode === 'FOUND' }" @click="searchMode = 'FOUND'">招领</button>
            <button type="button" :class="{ active: searchMode === 'LOST' }" @click="searchMode = 'LOST'">失物</button>
          </div>
          <label class="search-field">
            <Search :size="18" />
            <input v-model="searchQuery" type="search" placeholder="物品名称、地点、描述" />
          </label>
        </div>

        <div class="chip-row">
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

        <div class="item-grid">
          <template v-if="searchMode === 'FOUND'">
            <ItemCard v-for="item in visibleFoundItems" :key="item.id" kind="found" :item="item" />
          </template>
          <template v-else>
            <ItemCard v-for="item in visibleLostItems" :key="item.id" kind="lost" :item="item" />
          </template>
        </div>
      </section>

      <section v-else-if="navigation.activePage === 'publish'" class="page-stack">
        <div class="section-heading">
          <div>
            <span class="eyebrow">发布信息</span>
            <h1>发布信息</h1>
          </div>
          <div class="segmented small">
            <button type="button" :class="{ active: publishMode === 'LOST' }" @click="publishMode = 'LOST'">失物</button>
            <button type="button" :class="{ active: publishMode === 'FOUND' }" @click="publishMode = 'FOUND'">招领</button>
          </div>
        </div>

        <form v-if="publishMode === 'LOST'" class="form-grid" @submit.prevent="submitPublish">
          <label>
            <span>物品名称</span>
            <input v-model="lostForm.itemName" required maxlength="100" placeholder="白色 AirPods Pro" />
          </label>
          <label>
            <span>物品类别</span>
            <select v-model="lostForm.category">
              <option v-for="option in categoryOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
          <label>
            <span>丢失开始时间</span>
            <input v-model="lostForm.lostTimeStart" required />
          </label>
          <label>
            <span>丢失结束时间</span>
            <input v-model="lostForm.lostTimeEnd" required />
          </label>
          <label class="span-2">
            <span>丢失地点</span>
            <input v-model="lostForm.lostLocation" required maxlength="100" placeholder="图书馆二楼东侧自习区" />
          </label>
          <label class="span-2">
            <span>物品描述</span>
            <textarea v-model="lostForm.description" maxlength="500" rows="4" placeholder="颜色、品牌、特殊标记" />
          </label>
          <label class="span-2">
            <span>图片地址</span>
            <input v-model="lostForm.imageUrls" placeholder="上传接口返回 URL，多个用逗号分隔" />
          </label>
          <label class="checkbox-line span-2">
            <input v-model="lostForm.subscribeMatch" type="checkbox" />
            <span>发布后订阅匹配提醒</span>
          </label>
          <button class="primary-action span-2" type="submit">提交失物</button>
        </form>

        <form v-else class="form-grid" @submit.prevent="submitPublish">
          <label>
            <span>物品名称</span>
            <input v-model="foundForm.itemName" required maxlength="100" placeholder="校园一卡通" />
          </label>
          <label>
            <span>物品类别</span>
            <select v-model="foundForm.category">
              <option v-for="option in categoryOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
          <label>
            <span>拾获时间</span>
            <input v-model="foundForm.foundTime" required />
          </label>
          <label>
            <span>拾获地点</span>
            <input v-model="foundForm.foundLocation" required maxlength="100" placeholder="南区食堂二楼" />
          </label>
          <label>
            <span>保管方式</span>
            <select v-model="foundForm.custodyType">
              <option v-for="option in custodyOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
          <label>
            <span>联系方式偏好</span>
            <select v-model="foundForm.contactPreference">
              <option v-for="option in contactOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
          <label class="span-2">
            <span>验证问题</span>
            <input v-model="foundForm.verifyQuestion" maxlength="100" placeholder="请说出物品上的特殊标记" />
          </label>
          <label class="span-2">
            <span>答案关键词</span>
            <input v-model="foundForm.answerKeywords" placeholder="关键词用逗号分隔" />
          </label>
          <label class="span-2">
            <span>公开描述</span>
            <textarea v-model="foundForm.description" maxlength="500" rows="4" placeholder="发现位置、保管方式、可公开线索" />
          </label>
          <button class="primary-action span-2" type="submit">提交招领</button>
        </form>

        <p v-if="submitState" class="toast-line"><CheckCircle2 :size="18" />{{ submitState }}</p>
      </section>

      <section v-else-if="navigation.activePage === 'matches'" class="page-stack">
        <div class="section-heading">
          <div>
            <span class="eyebrow">MATCHES & CLAIMS</span>
            <h1>匹配与认领</h1>
          </div>
        </div>

        <div class="match-list">
          <article v-for="match in demoMatches" :key="match.matchId" class="match-row" :class="scoreTone(match.totalScore)">
            <div>
              <span class="eyebrow">{{ match.matchStatus }}</span>
              <h3>{{ match.counterpart.itemName }}</h3>
              <p>{{ match.counterpart.location }} · {{ timeShort(match.counterpart.time) }}</p>
            </div>
            <div class="match-score">
              <strong>{{ formatPercent(match.totalScore) }}</strong>
              <span>综合匹配</span>
            </div>
            <button class="secondary-action" type="button" :disabled="!match.canClaim">发起认领</button>
          </article>
        </div>

        <div class="claim-grid">
          <article v-for="claim in demoClaims" :key="claim.id" class="claim-card">
            <div>
              <span class="status-badge">{{ claimStatusLabels[claim.reviewStatus] }}</span>
              <h3>{{ claim.itemName }}</h3>
              <p>{{ verifyLevelLabels[claim.verifyLevel] }}</p>
            </div>
            <span>{{ claim.handoverLocation ?? '未安排交接' }}</span>
          </article>
        </div>
      </section>

      <section v-else-if="navigation.activePage === 'messages'" class="page-stack">
        <div class="section-heading">
          <div>
            <span class="eyebrow">消息通知</span>
            <h1>消息中心</h1>
          </div>
          <span class="status-badge strong">{{ unreadCount }} 未读</span>
        </div>

        <div class="message-list">
          <article v-for="notice in demoNotifications" :key="notice.id" class="message-row" :class="{ unread: !notice.isRead }">
            <MessageSquareText :size="22" />
            <div>
              <span>{{ noticeTypeLabels[notice.noticeType] }} · {{ notice.createdAt }}</span>
              <h3>{{ notice.title }}</h3>
              <p>{{ notice.content }}</p>
            </div>
          </article>
        </div>
      </section>

      <section v-else class="page-stack">
        <div class="profile-layout">
          <article class="profile-panel">
            <span class="avatar large">{{ demoUser.nickname.slice(0, 1) }}</span>
            <h1>{{ currentUser.nickname }}</h1>
            <p>{{ currentUser.phone }} · {{ currentUser.campusId ?? '未认证校园编号' }}</p>
            <span class="status-badge strong"><ShieldCheck :size="15" />已实名认证</span>
            <button type="button" class="secondary-action" @click="logout">退出登录</button>
          </article>

          <div class="profile-stats">
            <article>
              <Sparkles :size="22" />
              <strong>{{ currentUser.creditScore }}</strong>
              <span>信誉分</span>
            </article>
            <article>
              <Inbox :size="22" />
              <strong>{{ lostItems.length }}</strong>
              <span>我的发布</span>
            </article>
            <article>
              <PackageCheck :size="22" />
              <strong>{{ demoClaims.length }}</strong>
              <span>我的认领</span>
            </article>
          </div>
        </div>

        <div class="section-heading">
          <h2>我的失物</h2>
        </div>
        <div class="item-grid">
          <ItemCard v-for="item in lostItems" :key="item.id" kind="lost" :item="item" />
        </div>
      </section>
    </main>

    <nav class="bottom-tabs" aria-label="移动端主导航">
      <button
        v-for="item in navItems.slice(0, 5)"
        :key="item.key"
        type="button"
        :class="{ active: navigation.activePage === item.key }"
        @click="go(item.key)"
      >
        <component :is="item.icon" :size="20" />
        <span>{{ item.label }}</span>
      </button>
    </nav>
    </template>
  </div>
</template>
