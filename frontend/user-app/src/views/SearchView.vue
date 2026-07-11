<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Search } from '@element-plus/icons-vue';

import EmptyState from '@/components/EmptyState.vue';
import ItemCard from '@/components/ItemCard.vue';
import { listFoundItems, listLostItems } from '@/api/item';
import { ApiError, isAuthApiError } from '@/api/http';
import type {
  FoundItemStatus,
  FoundItemQuery,
  FoundItemSummary,
  ItemCategory,
  LostItemStatus,
  LostItemQuery,
  LostItemSummary,
  SortBy,
} from '@xunji/shared';
import { categoryOptions, foundStatusOptions, lostStatusOptions } from '@xunji/shared';
import {
  buildSearchQuery,
  parseSearchQuery,
  type SearchMode,
  type SearchState,
} from '@/utils/interaction';

const route = useRoute();
const router = useRouter();
const initialState = parseSearchQuery(route.query);
const mode = ref<SearchMode>(initialState.mode);
const keyword = ref(initialState.keyword);
const category = ref<ItemCategory | ''>(initialState.category);
const location = ref(initialState.location);
const eventRange = ref<[string, string] | []>(
  initialState.eventTimeStart && initialState.eventTimeEnd
    ? [initialState.eventTimeStart, initialState.eventTimeEnd]
    : [],
);
const status = ref<FoundItemStatus | LostItemStatus | ''>(initialState.status);
const sortBy = ref<SortBy>(initialState.sortBy);
const loading = ref(false);
const loadError = ref('');
const foundList = ref<FoundItemSummary[]>([]);
const lostList = ref<LostItemSummary[]>([]);
const total = ref(0);
const page = ref(initialState.page);
const pageSize = 12;

async function load() {
  loading.value = true;
  loadError.value = '';
  try {
    const common = {
      pageNo: page.value,
      pageSize,
      keyword: keyword.value.trim() || undefined,
      category: category.value || undefined,
      location: location.value.trim() || undefined,
      eventTimeStart: eventRange.value[0] || undefined,
      eventTimeEnd: eventRange.value[1] || undefined,
      sortBy: sortBy.value,
    };
    if (mode.value === 'FOUND') {
      const params: FoundItemQuery = {
        ...common,
        status: (status.value as FoundItemStatus) || undefined,
      };
      const data = await listFoundItems(params);
      foundList.value = data.list;
      lostList.value = [];
      total.value = data.total;
    } else {
      const params: LostItemQuery = {
        ...common,
        status: (status.value as LostItemStatus) || undefined,
      };
      const data = await listLostItems(params);
      lostList.value = data.list;
      foundList.value = [];
      total.value = data.total;
    }
  } catch (err) {
    if (isAuthApiError(err)) return;
    foundList.value = [];
    lostList.value = [];
    total.value = 0;
    loadError.value = err instanceof ApiError ? err.message : '搜索失败，请稍后重试';
  } finally {
    loading.value = false;
  }
}

const visibleList = computed(() => (mode.value === 'FOUND' ? foundList.value : lostList.value));
const statusOptions = computed(() => (mode.value === 'FOUND' ? foundStatusOptions : lostStatusOptions));

function openItem(id: string) {
  void router.push(`/items/${mode.value.toLowerCase()}/${id}`);
}

function currentState(): SearchState {
  return {
    mode: mode.value,
    keyword: keyword.value,
    category: category.value,
    location: location.value,
    eventTimeStart: eventRange.value[0] || '',
    eventTimeEnd: eventRange.value[1] || '',
    status: status.value,
    sortBy: sortBy.value,
    page: page.value,
  };
}

function applyState(state: SearchState) {
  mode.value = state.mode;
  keyword.value = state.keyword;
  category.value = state.category;
  location.value = state.location;
  eventRange.value = state.eventTimeStart && state.eventTimeEnd
    ? [state.eventTimeStart, state.eventTimeEnd]
    : [];
  status.value = state.status;
  sortBy.value = state.sortBy;
  page.value = state.page;
}

async function syncUrl(resetPage = false) {
  if (resetPage) page.value = 1;
  const target = { name: 'search', query: buildSearchQuery(currentState()) };
  if (router.resolve(target).fullPath === route.fullPath) {
    await load();
    return;
  }
  await router.push(target);
}

function changeMode() {
  status.value = '';
  void syncUrl(true);
}

function selectCategory(value: ItemCategory | '') {
  category.value = value;
  void syncUrl(true);
}

watch(
  () => route.fullPath,
  () => {
    applyState(parseSearchQuery(route.query));
    void load();
  },
);

onMounted(() => {
  const target = { name: 'search', query: buildSearchQuery(currentState()) };
  if (router.resolve(target).fullPath !== route.fullPath) {
    void router.replace(target);
  } else {
    void load();
  }
});
</script>

<template>
  <div class="page">
    <header class="page-header">
      <span class="eyebrow">Search</span>
      <h1>检索物品</h1>
      <p>按名称或描述搜索，并结合类别、地点、状态筛选</p>
    </header>

    <el-card shadow="never" class="filter-card">
      <el-radio-group v-model="mode" size="large" class="mode-toggle" @change="changeMode">
        <el-radio-button label="FOUND">招领信息</el-radio-button>
        <el-radio-button label="LOST">失物信息</el-radio-button>
      </el-radio-group>

      <el-input
        v-model="keyword"
        size="large"
        placeholder="物品名称或描述关键词"
        clearable
        @keyup.enter="syncUrl(true)"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
        <template #append>
          <el-button
            @click="syncUrl(true)"
            >搜索</el-button
          >
        </template>
      </el-input>

      <div class="chips">
        <el-check-tag :checked="category === ''" @change="selectCategory('')">全部</el-check-tag>
        <el-check-tag
          v-for="opt in categoryOptions"
          :key="opt.value"
          :checked="category === opt.value"
          @change="selectCategory(opt.value)"
        >
          {{ opt.label }}
        </el-check-tag>
      </div>

      <div class="advanced-filters">
        <el-input
          v-model="location"
          clearable
          placeholder="地点关键词，如：图书馆"
          @keyup.enter="syncUrl(true)"
        />
        <el-date-picker
          v-model="eventRange"
          type="datetimerange"
          value-format="YYYY-MM-DD HH:mm:ss"
          format="YYYY-MM-DD HH:mm"
          range-separator="至"
          start-placeholder="事件开始时间"
          end-placeholder="事件结束时间"
          @change="syncUrl(true)"
        />
        <el-select v-model="status" clearable placeholder="全部状态" @change="syncUrl(true)">
          <el-option
            v-for="opt in statusOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-select v-model="sortBy" @change="syncUrl(true)">
          <el-option label="最新发布" value="CREATED_DESC" />
          <el-option label="最早发布" value="CREATED_ASC" />
          <el-option label="事件时间从近到远" value="EVENT_DESC" />
          <el-option label="事件时间从远到近" value="EVENT_ASC" />
        </el-select>
        <el-button type="primary" @click="syncUrl(true)">应用筛选</el-button>
      </div>
    </el-card>

    <el-skeleton v-if="loading" :rows="4" animated />
    <template v-else>
      <EmptyState
        v-if="loadError"
        title="搜索结果加载失败"
        :description="loadError"
        action-text="重试"
        @action="load"
      />
      <div v-else-if="visibleList.length" class="grid">
        <ItemCard
          v-for="item in visibleList"
          :key="item.id"
          :kind="mode === 'FOUND' ? 'found' : 'lost'"
          :item="item"
          @open="openItem"
        />
      </div>
      <EmptyState v-else title="未找到符合条件的物品" description="试试调整关键词或筛选条件" />

      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        background
        class="pagination"
        @current-change="syncUrl(false)"
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

.advanced-filters {
  display: grid;
  grid-template-columns: minmax(160px, 1fr) minmax(300px, 1.4fr) 150px 160px auto;
  gap: 10px;
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

@media (max-width: 720px) {
  .advanced-filters {
    grid-template-columns: 1fr;

    .el-button {
      width: 100%;
    }
  }
}
</style>
