<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { Aim, Bell, Document, Medal, Plus, Right, Search } from '@element-plus/icons-vue';

import EmptyState from '@/components/EmptyState.vue';
import ItemCard from '@/components/ItemCard.vue';
import { listFoundItems } from '@/api/item';
import { listNotifications } from '@/api/notification';
import { ApiError, isAuthApiError } from '@/api/http';
import { useAuthStore } from '@/stores/auth';
import { useNotificationStore } from '@/stores/notification';
import type { FoundItemSummary, NotificationSummary } from '@xunji/shared';
import { noticeTypeLabels } from '@xunji/shared';
import { relativeTime } from '@/utils/format';

const router = useRouter();
const auth = useAuthStore();
const notice = useNotificationStore();

const recentFound = ref<FoundItemSummary[]>([]);
const recentNotifications = ref<NotificationSummary[]>([]);
const pendingFoundTotal = ref<number | null>(null);
const foundLoading = ref(true);
const notificationLoading = ref(true);
const foundError = ref('');
const notificationError = ref('');

const stats = computed(() => [
  { label: '我的信誉分', value: auth.profile?.creditScore ?? '—', note: '来自信誉积分记录' },
  { label: '我的未读消息', value: notice.unreadTotal, note: '当前账号实时未读' },
  { label: '待领取招领', value: pendingFoundTotal.value ?? '—', note: '全站当前可认领总数' },
]);

async function loadFound() {
  foundLoading.value = true;
  foundError.value = '';
  try {
    const foundPage = await listFoundItems({ pageSize: 6, status: 'PENDING' });
    recentFound.value = foundPage.list;
    pendingFoundTotal.value = foundPage.total;
  } catch (err) {
    if (isAuthApiError(err)) return;
    foundError.value = err instanceof ApiError ? err.message : '最新招领加载失败';
  } finally {
    foundLoading.value = false;
  }
}

async function loadNotifications() {
  notificationLoading.value = true;
  notificationError.value = '';
  try {
    const notiPage = await listNotifications({ pageSize: 4 });
    recentNotifications.value = notiPage.list;
  } catch (err) {
    if (isAuthApiError(err)) return;
    notificationError.value = err instanceof ApiError ? err.message : '消息提醒加载失败';
  } finally {
    notificationLoading.value = false;
  }
}

async function load() {
  await Promise.allSettled([loadFound(), loadNotifications()]);
}

function openItem(id: string) {
  void router.push(`/items/found/${id}`);
}

onMounted(load);
</script>

<template>
  <div class="page">
    <section class="hero xunji-hero">
      <div class="hero-text">
        <span class="eyebrow">Hi, {{ auth.displayName }}</span>
        <h1>今天有什么需要帮助的？</h1>
        <p>发布失物或招领，AI 自动匹配相似线索</p>
      </div>
      <div class="hero-actions">
        <el-button size="large" type="primary" plain @click="router.push('/publish/lost')">
          <el-icon><Plus /></el-icon>
          <span>发布失物</span>
        </el-button>
        <el-button size="large" color="#7c3aed" @click="router.push('/publish/found')">
          <el-icon><Document /></el-icon>
          <span>登记招领</span>
        </el-button>
      </div>
    </section>

    <section class="latest-section">
      <header class="section-header">
        <div>
          <span class="eyebrow">刚刚被找到</span>
          <h2>最新招领</h2>
        </div>
        <RouterLink class="section-link" to="/search">查看全部 <el-icon><Right /></el-icon></RouterLink>
      </header>
      <el-skeleton v-if="foundLoading && !recentFound.length" :rows="3" animated />
      <EmptyState
        v-else-if="foundError && !recentFound.length"
        title="最新招领加载失败"
        :description="foundError"
        action-text="重试"
        @action="loadFound"
      />
      <el-alert
        v-else-if="foundError"
        type="warning"
        :closable="false"
        :title="`${foundError}，当前保留上次成功结果`"
      >
        <template #default><el-button link type="primary" @click="loadFound">重试</el-button></template>
      </el-alert>
      <div v-if="recentFound.length" v-loading="foundLoading" class="grid">
        <ItemCard
          v-for="item in recentFound.slice(0, 6)"
          :key="item.id"
          kind="found"
          :item="item"
          @open="openItem"
        />
      </div>
      <EmptyState
        v-else-if="!foundError && !foundLoading"
        title="暂无招领信息"
        description="成为第一个登记招领的同学吧"
        action-text="去登记"
        @action="router.push('/publish/found')"
      />
    </section>

    <section class="quick-section">
      <header class="section-header compact">
        <div>
          <span class="eyebrow">常用业务</span>
          <h2>接下来做什么</h2>
        </div>
      </header>
      <div class="quick-grid">
        <RouterLink to="/search" class="quick-card">
          <span class="quick-icon"><el-icon :size="21"><Search /></el-icon></span>
          <span class="quick-copy">
            <strong>检索物品</strong>
            <small>浏览全站失物与招领线索</small>
          </span>
          <el-icon class="arrow"><Right /></el-icon>
        </RouterLink>
        <RouterLink to="/matches" class="quick-card">
          <span class="quick-icon accent"><el-icon :size="21"><Aim /></el-icon></span>
          <span class="quick-copy">
            <strong>查看匹配</strong>
            <small>查看与你失物相符的线索</small>
          </span>
          <el-icon class="arrow"><Right /></el-icon>
        </RouterLink>
        <RouterLink to="/claims" class="quick-card">
          <span class="quick-icon warm"><el-icon :size="21"><Document /></el-icon></span>
          <span class="quick-copy">
            <strong>我的认领</strong>
            <small>跟进进度与交接凭证</small>
          </span>
          <el-icon class="arrow"><Right /></el-icon>
        </RouterLink>
      </div>
    </section>

    <section class="trust-section">
      <header class="section-header compact">
        <div>
          <span class="eyebrow">实时概览</span>
          <h2>可信数据</h2>
        </div>
        <el-icon class="trust-mark" :size="20"><Medal /></el-icon>
      </header>
      <div class="stats">
        <div v-for="s in stats" :key="s.label" class="stat-card">
          <div class="stat-value">{{ s.value }}</div>
          <div class="stat-copy">
            <strong>{{ s.label }}</strong>
            <small>{{ s.note }}</small>
          </div>
        </div>
      </div>
    </section>

    <section class="notice-section">
      <header class="section-header">
        <div>
          <span class="eyebrow">与你有关</span>
          <h2>消息提醒</h2>
        </div>
        <RouterLink class="section-link" to="/notifications">全部消息 <el-icon><Right /></el-icon></RouterLink>
      </header>
      <el-card shadow="never" class="notice-card">
        <el-skeleton v-if="notificationLoading && !recentNotifications.length" :rows="3" animated />
        <EmptyState
          v-else-if="notificationError && !recentNotifications.length"
          title="消息提醒加载失败"
          :description="notificationError"
          action-text="重试"
          @action="loadNotifications"
        />
        <el-alert
          v-else-if="notificationError"
          type="warning"
          :closable="false"
          :title="`${notificationError}，当前保留上次成功结果`"
        >
          <template #default><el-button link type="primary" @click="loadNotifications">重试</el-button></template>
        </el-alert>
        <template v-if="recentNotifications.length">
          <RouterLink
            v-for="n in recentNotifications"
            :key="n.id"
            to="/notifications"
            class="notice-row"
          >
            <el-icon :size="18" :color="n.isRead ? 'var(--xunji-text-muted)' : 'var(--el-color-primary)'">
              <Bell />
            </el-icon>
            <div class="notice-body">
              <strong>{{ n.title }}</strong>
              <small>{{ noticeTypeLabels[n.noticeType] }} · {{ relativeTime(n.createdAt) }}</small>
            </div>
            <el-tag v-if="!n.isRead" size="small" type="primary">未读</el-tag>
            <el-icon class="notice-arrow"><Right /></el-icon>
          </RouterLink>
        </template>
        <EmptyState v-else-if="!notificationError && !notificationLoading" title="暂无消息提醒" />
      </el-card>
    </section>
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-width: 0;

  > section {
    min-width: 0;
  }
}

.hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 18px;
  padding: 28px 32px;
  color: #fff;

  .eyebrow {
    display: inline-block;
    padding: 4px 10px;
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.12);
    font-size: 12px;
    letter-spacing: 0.08em;
  }

  h1 {
    margin: 10px 0 4px;
    font-size: clamp(21px, 3vw, 26px);
    font-weight: 700;
    letter-spacing: -0.02em;
  }

  p {
    margin: 0;
    color: rgba(255, 255, 255, 0.82);
    font-size: 13px;
  }

  .hero-actions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;

    .el-button {
      min-height: 44px;
      margin-left: 0;
    }
  }
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;

  &.compact {
    margin-bottom: 14px;
  }

  .eyebrow {
    color: var(--xunji-primary);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
  }

  h2 {
    margin: 3px 0 0;
    color: var(--xunji-text);
    font-size: 19px;
    letter-spacing: -0.01em;
  }
}

.section-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  gap: 2px;
  min-height: 44px;
  padding: 0 4px 0 10px;
  color: var(--xunji-primary);
  font-size: 13px;
  font-weight: 600;

  &:focus-visible {
    border-radius: 8px;
    outline: 3px solid rgba(13, 79, 79, 0.18);
  }
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(240px, 100%), 1fr));
  gap: 16px;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.quick-card {
  display: flex;
  align-items: center;
  min-width: 0;
  min-height: 76px;
  gap: 12px;
  padding: 15px;
  border: 1px solid var(--xunji-border);
  border-radius: var(--xunji-radius);
  background: var(--xunji-surface);
  box-shadow: var(--xunji-shadow-sm);
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.18s;

  .quick-icon {
    display: grid;
    place-items: center;
    flex: 0 0 40px;
    width: 40px;
    height: 40px;
    border-radius: 11px;
    background: #e7f1f0;
    color: var(--xunji-primary);

    &.accent {
      background: var(--xunji-accent-soft);
      color: var(--xunji-accent);
    }

    &.warm {
      background: #fef3df;
      color: #b97608;
    }
  }

  .quick-copy {
    min-width: 0;
    flex: 1;
  }

  strong,
  small {
    display: block;
  }

  strong {
    color: var(--xunji-text);
    font-size: 14px;
    font-weight: 650;
  }

  small {
    margin-top: 3px;
    color: var(--xunji-text-muted);
    font-size: 12px;
    line-height: 1.35;
  }

  .arrow {
    flex: 0 0 auto;
    color: #94a3b8;
  }

  &:focus-visible {
    outline: 3px solid rgba(13, 79, 79, 0.18);
    outline-offset: 2px;
  }

  @media (hover: hover) {
    &:hover {
      border-color: #b6d6d6;
      box-shadow: var(--xunji-shadow);
      transform: translateY(-2px);
    }
  }
}

.trust-section {
  padding: 18px 20px 20px;
  border: 1px solid #d9e8e6;
  border-radius: var(--xunji-radius);
  background: #f0f6f5;

  .trust-mark {
    color: var(--xunji-primary);
  }
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  overflow: hidden;
  border: 1px solid #d9e8e6;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
}

.stat-card {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 12px;
  padding: 16px;
  border-right: 1px solid #d9e8e6;

  &:last-child {
    border-right: 0;
  }

  .stat-value {
    min-width: 36px;
    color: var(--xunji-primary-dark);
    font-size: 25px;
    font-weight: 750;
    line-height: 1;
    text-align: center;
  }

  .stat-copy {
    min-width: 0;

    strong,
    small {
      display: block;
    }

    strong {
      color: var(--xunji-text);
      font-size: 13px;
      font-weight: 650;
    }

    small {
      margin-top: 3px;
      color: var(--xunji-text-muted);
      font-size: 11px;
      line-height: 1.35;
    }
  }
}

.notice-card {
  overflow: hidden;

  :deep(.el-card__body) {
    padding: 0;
  }
}

.notice-row {
  display: flex;
  align-items: center;
  min-height: 58px;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--xunji-border);
  transition: background 0.18s;

  &:last-child {
    border-bottom: none;
  }

  &:focus-visible {
    outline: 3px solid rgba(13, 79, 79, 0.18);
    outline-offset: -3px;
  }

  .notice-body {
    flex: 1;
    min-width: 0;

    strong {
      display: block;
      overflow: hidden;
      color: var(--xunji-text);
      font-weight: 600;
      font-size: 14px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    small {
      display: block;
      margin-top: 2px;
      color: var(--xunji-text-muted);
      font-size: 12px;
    }
  }

  .notice-arrow {
    flex: 0 0 auto;
    color: #94a3b8;
  }

  @media (hover: hover) {
    &:hover {
      background: rgba(13, 79, 79, 0.04);
    }
  }
}

@media (max-width: 880px) {
  .quick-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .quick-card:last-child {
    grid-column: 1 / -1;
  }

  .stats {
    grid-template-columns: 1fr;
  }

  .stat-card {
    border-right: 0;
    border-bottom: 1px solid #d9e8e6;

    &:last-child {
      border-bottom: 0;
    }
  }

  .hero {
    padding: 22px;
  }
}

@media (max-width: 560px) {
  .page {
    gap: 22px;
  }

  .hero {
    padding: 20px 18px;

    .hero-actions {
      width: 100%;

      .el-button {
        flex: 1 1 0;
        padding-right: 12px;
        padding-left: 12px;
      }
    }
  }

  .quick-grid {
    grid-template-columns: 1fr;
  }

  .quick-card:last-child {
    grid-column: auto;
  }

  .trust-section {
    padding: 16px;
  }

  .notice-row {
    gap: 9px;
    padding: 10px 12px;

    .notice-arrow {
      display: none;
    }
  }
}
</style>
