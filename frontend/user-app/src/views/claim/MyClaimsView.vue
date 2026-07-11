<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import EmptyState from '@/components/EmptyState.vue';
import StatusTag from '@/components/StatusTag.vue';
import { listMyClaims } from '@/api/claim';
import { ApiError, isAuthApiError } from '@/api/http';
import type {
  ClaimMyRole,
  ClaimSummary,
} from '@xunji/shared';
import { verifyLevelLabels } from '@xunji/shared';
import { shortDateTime } from '@/utils/format';

const router = useRouter();
const role = ref<ClaimMyRole>('CLAIMANT');
const list = ref<ClaimSummary[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 10;
const loading = ref(true);
const loadError = ref('');

async function load() {
  loading.value = true;
  loadError.value = '';
  try {
    const data = await listMyClaims({ role: role.value, pageNo: page.value, pageSize });
    list.value = data.list;
    total.value = data.total;
  } catch (err) {
    if (isAuthApiError(err)) return;
    list.value = [];
    total.value = 0;
    loadError.value = err instanceof ApiError ? err.message : '认领记录加载失败，请稍后重试';
  } finally {
    loading.value = false;
  }
}

watch(role, () => {
  page.value = 1;
  void load();
});

onMounted(load);
</script>

<template>
  <div class="page">
    <header class="page-header">
      <span class="eyebrow">Claims</span>
      <h1>我的认领</h1>
      <p>跟进认领进度，及时回复审核与凭证</p>
    </header>

    <el-radio-group v-model="role" size="large">
      <el-radio-button label="CLAIMANT">我发起的</el-radio-button>
      <el-radio-button label="FINDER">我审核的</el-radio-button>
    </el-radio-group>

    <el-skeleton v-if="loading" :rows="3" animated />

    <template v-else>
      <EmptyState
        v-if="loadError"
        title="认领记录加载失败"
        :description="loadError"
        action-text="重试"
        @action="load"
      />
      <div v-else-if="list.length" class="grid">
        <el-card
          v-for="c in list"
          :key="c.id"
          shadow="never"
          class="claim-card"
          @click="router.push(`/claims/${c.id}`)"
        >
          <div class="head">
            <strong>{{ c.itemName }}</strong>
            <StatusTag variant="claim" :value="c.reviewStatus" />
          </div>
          <div class="meta">
            <span>{{ verifyLevelLabels[c.verifyLevel] }}</span>
            <span>更新 {{ shortDateTime(c.updatedAt) }}</span>
          </div>
        </el-card>
      </div>
      <EmptyState v-else title="暂无认领记录" description="发现匹配的招领后，可以发起认领申请" />

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
    </template>
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.page-header {
  .eyebrow {
    color: var(--xunji-text-muted);
    font-size: 12px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }
  h1 {
    margin: 6px 0 4px;
    font-size: 22px;
  }
  p {
    margin: 0;
    color: var(--xunji-text-muted);
    font-size: 13px;
  }
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}
.claim-card {
  cursor: pointer;
  transition: transform 0.18s, box-shadow 0.18s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--xunji-shadow);
  }

  .head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    strong {
      font-weight: 600;
      font-size: 15px;
    }
  }
  .meta {
    display: flex;
    justify-content: space-between;
    color: var(--xunji-text-muted);
    font-size: 12px;
  }
}
.pagination {
  justify-content: center;
}
</style>
