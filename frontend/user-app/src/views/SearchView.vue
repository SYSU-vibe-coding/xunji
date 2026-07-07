<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { Search } from '@element-plus/icons-vue';

import EmptyState from '@/components/EmptyState.vue';
import ItemCard from '@/components/ItemCard.vue';
import { listFoundItems, listLostItems } from '@/api/item';
import { isAuthApiError } from '@/api/http';
import type {
  FoundItemQuery,
  FoundItemSummary,
  ItemCategory,
  LostItemQuery,
  LostItemSummary,
} from '@xunji/shared';
import { categoryOptions } from '@xunji/shared';

const router = useRouter();
const mode = ref<'FOUND' | 'LOST'>('FOUND');
const keyword = ref('');
const category = ref<ItemCategory | ''>('');
const loading = ref(false);
const foundList = ref<FoundItemSummary[]>([]);
const lostList = ref<LostItemSummary[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 12;

async function load() {
  loading.value = true;
  try {
    const params: FoundItemQuery & LostItemQuery = {
      pageNo: page.value,
      pageSize,
      keyword: keyword.value || undefined,
      category: category.value || undefined,
    };
    if (mode.value === 'FOUND') {
      const data = await listFoundItems(params);
      foundList.value = data.list;
      total.value = data.total;
    } else {
      const data = await listLostItems(params);
      lostList.value = data.list;
      total.value = data.total;
    }
  } catch (err) {
    if (isAuthApiError(err)) return;
    foundList.value = [];
    lostList.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

const visibleList = computed(() => (mode.value === 'FOUND' ? foundList.value : lostList.value));

function openItem(id: string) {
  void router.push(`/items/${mode.value.toLowerCase()}/${id}`);
}

watch([mode, category], () => {
  page.value = 1;
  void load();
});

onMounted(load);
</script>

<template>
  <div class="page">
    <header class="page-header">
      <span class="eyebrow">Search</span>
      <h1>检索物品</h1>
      <p>切换招领 / 失物，按关键词、类别筛选</p>
    </header>

    <el-card shadow="never" class="filter-card">
      <el-radio-group v-model="mode" size="large" class="mode-toggle">
        <el-radio-button label="FOUND">招领信息</el-radio-button>
        <el-radio-button label="LOST">失物信息</el-radio-button>
      </el-radio-group>

      <el-input
        v-model="keyword"
        size="large"
        placeholder="物品名称、地点、描述关键词"
        clearable
        @keyup.enter="
          () => {
            page = 1;
            load();
          }
        "
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
        <template #append>
          <el-button
            @click="
              () => {
                page = 1;
                load();
              }
            "
            >搜索</el-button
          >
        </template>
      </el-input>

      <div class="chips">
        <el-check-tag :checked="category === ''" @change="category = ''">全部</el-check-tag>
        <el-check-tag
          v-for="opt in categoryOptions"
          :key="opt.value"
          :checked="category === opt.value"
          @change="category = opt.value"
        >
          {{ opt.label }}
        </el-check-tag>
      </div>
    </el-card>

    <el-skeleton v-if="loading" :rows="4" animated />
    <template v-else>
      <div v-if="visibleList.length" class="grid">
        <ItemCard
          v-for="item in visibleList"
          :key="item.id"
          :kind="mode === 'FOUND' ? 'found' : 'lost'"
          :item="item"
          @open="openItem"
        />
      </div>
      <EmptyState v-else title="未找到符合条件的物品" description="试试调整关键词或类别筛选" />

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

.filter-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.pagination {
  margin-top: 8px;
  justify-content: center;
}
</style>
