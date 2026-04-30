<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { Aim, Bell, Document, Plus, Right, Search } from '@element-plus/icons-vue';

import EmptyState from '@/components/EmptyState.vue';
import ItemCard from '@/components/ItemCard.vue';
import { listFoundItems } from '@/api/item';
import { listNotifications } from '@/api/notification';
import { ApiError } from '@/api/http';
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
const loading = ref(true);

const stats = computed(() => [
  { label: '信誉分', value: auth.profile?.creditScore ?? 0, suffix: '' },
  { label: '未读消息', value: notice.unreadTotal, suffix: '' },
  { label: '招领待领取', value: recentFound.value.filter((it) => it.status === 'PENDING').length, suffix: '' },
]);

async function load() {
  loading.value = true;
  try {
    const [foundPage, notiPage] = await Promise.all([
      listFoundItems({ pageSize: 6, status: 'PENDING' }),
      listNotifications({ pageSize: 4 }),
    ]);
    recentFound.value = foundPage.list;
    recentNotifications.value = notiPage.list;
  } catch (err) {
    if (!(err instanceof ApiError) || err.code !== 40002) {
      // 静默：登录失效会被守卫接管
    }
  } finally {
    loading.value = false;
  }
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

    <section class="stats">
      <el-card v-for="s in stats" :key="s.label" shadow="never" class="stat-card">
        <div class="stat-label">{{ s.label }}</div>
        <div class="stat-value">{{ s.value }}{{ s.suffix }}</div>
      </el-card>
    </section>

    <section class="quick-grid">
      <el-card shadow="never" class="quick-card" @click="router.push('/search')">
        <el-icon :size="22"><Search /></el-icon>
        <div>
          <strong>检索物品</strong>
          <small>关键词、地点、类别快速过滤</small>
        </div>
        <el-icon class="arrow"><Right /></el-icon>
      </el-card>
      <el-card shadow="never" class="quick-card" @click="router.push('/matches')">
        <el-icon :size="22"><Aim /></el-icon>
        <div>
          <strong>查看匹配</strong>
          <small>AI 推荐与你失物相符的线索</small>
        </div>
        <el-icon class="arrow"><Right /></el-icon>
      </el-card>
      <el-card shadow="never" class="quick-card" @click="router.push('/claims')">
        <el-icon :size="22"><Document /></el-icon>
        <div>
          <strong>我的认领</strong>
          <small>跟进认领进度与凭证</small>
        </div>
        <el-icon class="arrow"><Right /></el-icon>
      </el-card>
    </section>

    <section>
      <header class="section-header">
        <div>
          <span class="eyebrow">Latest Found</span>
          <h2>最新招领</h2>
        </div>
        <el-button link type="primary" @click="router.push('/search')">查看全部</el-button>
      </header>
      <el-skeleton v-if="loading" :rows="3" animated />
      <div v-else-if="recentFound.length" class="grid">
        <ItemCard
          v-for="item in recentFound.slice(0, 6)"
          :key="item.id"
          kind="found"
          :item="item"
          @open="openItem"
        />
      </div>
      <EmptyState
        v-else
        title="暂无招领信息"
        description="成为第一个登记招领的同学吧"
        action-text="去登记"
        @action="router.push('/publish/found')"
      />
    </section>

    <section>
      <header class="section-header">
        <div>
          <span class="eyebrow">Notifications</span>
          <h2>消息提醒</h2>
        </div>
        <el-button link type="primary" @click="router.push('/notifications')">全部消息</el-button>
      </header>
      <el-card shadow="never" class="notice-card">
        <template v-if="recentNotifications.length">
          <div
            v-for="n in recentNotifications"
            :key="n.id"
            class="notice-row"
            @click="router.push('/notifications')"
          >
            <el-icon :size="18" :color="n.isRead ? 'var(--xunji-text-muted)' : 'var(--el-color-primary)'">
              <Bell />
            </el-icon>
            <div class="notice-body">
              <strong>{{ n.title }}</strong>
              <small>{{ noticeTypeLabels[n.noticeType] }} · {{ relativeTime(n.createdAt) }}</small>
            </div>
            <el-tag v-if="!n.isRead" size="small" type="primary">未读</el-tag>
          </div>
        </template>
        <EmptyState v-else title="暂无消息提醒" />
      </el-card>
    </section>
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.hero {
  padding: 28px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 18px;
  color: #fff;

  .hero-text {
    .eyebrow {
      display: inline-block;
      padding: 4px 10px;
      background: rgba(255, 255, 255, 0.18);
      border-radius: 999px;
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }
    h1 {
      margin: 10px 0 4px;
      font-size: 24px;
      font-weight: 700;
    }
    p {
      margin: 0;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.82);
    }
  }

  .hero-actions {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;

  .stat-card {
    border-radius: var(--xunji-radius);

    .stat-label {
      color: var(--xunji-text-muted);
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }
    .stat-value {
      margin-top: 6px;
      font-size: 26px;
      font-weight: 700;
      color: var(--xunji-text);
    }
  }
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;

  .quick-card {
    cursor: pointer;
    transition: transform 0.18s, box-shadow 0.18s;

    :deep(.el-card__body) {
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 18px;
    }

    .arrow {
      margin-left: auto;
      color: var(--xunji-text-muted);
    }

    strong {
      display: block;
      font-weight: 600;
    }
    small {
      color: var(--xunji-text-muted);
      font-size: 12px;
    }

    &:hover {
      transform: translateY(-2px);
      box-shadow: var(--xunji-shadow);
    }
  }
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;

  .eyebrow {
    color: var(--xunji-text-muted);
    font-size: 12px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }
  h2 {
    margin: 4px 0 0;
    font-size: 18px;
  }
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.notice-card {
  :deep(.el-card__body) {
    padding: 6px 0;
  }
}

.notice-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  cursor: pointer;
  border-bottom: 1px solid var(--xunji-border);

  &:last-child {
    border-bottom: none;
  }
  &:hover {
    background: rgba(13, 79, 79, 0.04);
  }

  .notice-body {
    flex: 1;
    strong {
      display: block;
      font-weight: 600;
      font-size: 14px;
    }
    small {
      color: var(--xunji-text-muted);
      font-size: 12px;
    }
  }
}

@media (max-width: 880px) {
  .stats,
  .quick-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .hero {
    padding: 22px;
    .hero-text h1 {
      font-size: 20px;
    }
  }
}
@media (max-width: 560px) {
  .stats,
  .quick-grid {
    grid-template-columns: 1fr;
  }
}
</style>
