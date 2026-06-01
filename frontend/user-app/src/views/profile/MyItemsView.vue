<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';

import EmptyState from '@/components/EmptyState.vue';
import ItemCard from '@/components/ItemCard.vue';
import { deleteLostItem, listFoundItems, listLostItems } from '@/api/item';
import { ApiError } from '@/api/http';
import { useAuthStore } from '@/stores/auth';
import type { FoundItemSummary, LostItemSummary } from '@xunji/shared';

const router = useRouter();
const auth = useAuthStore();

const tab = ref<'lost' | 'found'>('lost');
const lostList = ref<LostItemSummary[]>([]);
const foundList = ref<FoundItemSummary[]>([]);
const loading = ref(true);

async function load() {
  loading.value = true;
  if (!auth.profile) await auth.loadProfile().catch(() => {});
  try {
    const [lostPage, foundPage] = await Promise.all([
      listLostItems({ pageSize: 50 }),
      listFoundItems({ pageSize: 50 }),
    ]);
    // 仅保留我自己的发布
    const myId = auth.profile?.id ?? '';
    lostList.value = lostPage.list.filter((it) => it.userId === myId);
    foundList.value = foundPage.list.filter((it) => it.userId === myId);
  } catch (err) {
    if (err instanceof ApiError && err.code === 40002) return;
    lostList.value = [];
    foundList.value = [];
  } finally {
    loading.value = false;
  }
}

const visibleList = computed(() => (tab.value === 'lost' ? lostList.value : foundList.value));

function open(id: string) {
  void router.push(`/items/${tab.value}/${id}`);
}

async function handleDelete(id: string) {
  try {
    await ElMessageBox.confirm('确认删除这条失物信息吗？', '删除确认', { type: 'warning' });
  } catch {
    return;
  }
  try {
    await deleteLostItem(id);
    ElMessage.success('已删除');
    await load();
  } catch (err) {
    ElMessage.error(err instanceof ApiError ? err.message : '删除失败');
  }
}

watch(tab, () => {
  /* tab 切换不重新拉取，只过滤已加载的数据 */
});

onMounted(load);
</script>

<template>
  <div class="page">
    <header class="page-header">
      <span class="eyebrow">My posts</span>
      <h1>我的发布</h1>
      <p>编辑、删除你发布过的失物 / 招领</p>
    </header>

    <el-radio-group v-model="tab" size="large">
      <el-radio-button label="lost">失物 ({{ lostList.length }})</el-radio-button>
      <el-radio-button label="found">招领 ({{ foundList.length }})</el-radio-button>
    </el-radio-group>

    <el-skeleton v-if="loading" :rows="4" animated />
    <template v-else>
      <div v-if="visibleList.length" class="grid">
        <div v-for="item in visibleList" :key="item.id" class="cell">
          <ItemCard :kind="tab === 'lost' ? 'lost' : 'found'" :item="item" @open="open" />
          <div v-if="tab === 'lost'" class="cell-actions">
            <el-button size="small" plain @click="open(item.id)">查看</el-button>
            <el-button size="small" type="danger" plain @click="handleDelete(item.id)">删除</el-button>
          </div>
        </div>
      </div>
      <EmptyState
        v-else
        :title="tab === 'lost' ? '还没有发布过失物' : '还没有发布过招领'"
        action-text="去发布"
        @action="router.push(tab === 'lost' ? '/publish/lost' : '/publish/found')"
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
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
.cell {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.cell-actions {
  display: flex;
  gap: 6px;
}
</style>
