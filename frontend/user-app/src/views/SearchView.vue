<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Filter, Search } from '@element-plus/icons-vue';

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
const filterDrawerVisible = ref(false);
const draftLocation = ref('');
const draftEventRange = ref<[string, string] | []>([]);
const draftStatus = ref<FoundItemStatus | LostItemStatus | ''>('');
const draftSortBy = ref<SortBy>('CREATED_DESC');
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
const appliedAdvancedCount = computed(
  () =>
    Number(Boolean(location.value.trim())) +
    Number(eventRange.value.length === 2) +
    Number(Boolean(status.value)) +
    Number(sortBy.value !== 'CREATED_DESC'),
);

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

function openAdvancedFilters() {
  draftLocation.value = location.value;
  draftEventRange.value = eventRange.value.length === 2 ? [...eventRange.value] : [];
  draftStatus.value = status.value;
  draftSortBy.value = sortBy.value;
  filterDrawerVisible.value = true;
}

function resetAdvancedDraft() {
  draftLocation.value = '';
  draftEventRange.value = [];
  draftStatus.value = '';
  draftSortBy.value = 'CREATED_DESC';
}

function applyAdvancedFilters() {
  location.value = draftLocation.value;
  eventRange.value = draftEventRange.value.length === 2 ? [...draftEventRange.value] : [];
  status.value = draftStatus.value;
  sortBy.value = draftSortBy.value;
  filterDrawerVisible.value = false;
  void syncUrl(true);
}

watch(
  () => route.fullPath,
  () => {
    applyState(parseSearchQuery(route.query));
    filterDrawerVisible.value = false;
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

      <div class="advanced-filters desktop-filters">
        <el-input
          v-model="location"
          class="location-filter"
          clearable
          placeholder="地点关键词，如：图书馆"
          @keyup.enter="syncUrl(true)"
        />
        <el-date-picker
          v-model="eventRange"
          class="date-filter"
          type="datetimerange"
          value-format="YYYY-MM-DD HH:mm:ss"
          format="YYYY-MM-DD HH:mm"
          range-separator="至"
          start-placeholder="事件开始时间"
          end-placeholder="事件结束时间"
          @change="syncUrl(true)"
        />
        <el-select
          v-model="status"
          class="status-filter"
          clearable
          placeholder="全部状态"
          @change="syncUrl(true)"
        >
          <el-option
            v-for="opt in statusOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <el-select v-model="sortBy" class="sort-filter" @change="syncUrl(true)">
          <el-option label="最新发布" value="CREATED_DESC" />
          <el-option label="最早发布" value="CREATED_ASC" />
          <el-option label="事件时间从近到远" value="EVENT_DESC" />
          <el-option label="事件时间从远到近" value="EVENT_ASC" />
        </el-select>
        <el-button class="apply-button" type="primary" @click="syncUrl(true)">应用筛选</el-button>
      </div>

      <el-button class="mobile-filter-button" plain @click="openAdvancedFilters">
        <el-icon><Filter /></el-icon>
        <span>高级筛选</span>
        <span class="filter-count">已生效 {{ appliedAdvancedCount }} 项</span>
      </el-button>
    </el-card>

    <div class="result-summary" aria-live="polite">
      <strong>{{ mode === 'FOUND' ? '招领结果' : '失物结果' }}</strong>
      <span v-if="!loading && !loadError">共 {{ total }} 条</span>
    </div>

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
        :pager-count="5"
        layout="prev, pager, next"
        background
        class="pagination"
        @current-change="syncUrl(false)"
      />
    </template>

    <el-drawer
      v-model="filterDrawerVisible"
      class="mobile-filter-drawer"
      direction="btt"
      size="min(82dvh, 640px)"
      title="高级筛选"
      append-to-body
    >
      <p class="drawer-description">按地点、发生时间和当前状态缩小范围</p>
      <el-form label-position="top" class="drawer-form">
        <el-form-item label="地点">
          <el-input
            v-model="draftLocation"
            clearable
            placeholder="如：图书馆、东区食堂"
            @keyup.enter="applyAdvancedFilters"
          />
        </el-form-item>
        <el-form-item label="事件时间">
          <el-date-picker
            v-model="draftEventRange"
            type="datetimerange"
            value-format="YYYY-MM-DD HH:mm:ss"
            format="YYYY-MM-DD HH:mm"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="draftStatus" clearable placeholder="全部状态">
            <el-option
              v-for="opt in statusOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-select v-model="draftSortBy">
            <el-option label="最新发布" value="CREATED_DESC" />
            <el-option label="最早发布" value="CREATED_ASC" />
            <el-option label="事件时间从近到远" value="EVENT_DESC" />
            <el-option label="事件时间从远到近" value="EVENT_ASC" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="drawer-actions">
          <el-button plain @click="resetAdvancedDraft">重置</el-button>
          <el-button type="primary" @click="applyAdvancedFilters">应用筛选</el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped lang="scss">
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}

.page-header {
  .eyebrow {
    color: var(--xunji-primary);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
  }

  h1 {
    margin: 5px 0 4px;
    font-size: 24px;
    letter-spacing: -0.02em;
  }

  p {
    margin: 0;
    color: var(--xunji-text-muted);
    font-size: 13px;
  }
}

.filter-card {
  overflow: visible;

  :deep(.el-card__body) {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 20px;
  }
}

.mode-toggle {
  align-self: flex-start;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;

  :deep(.el-check-tag) {
    display: inline-flex;
    align-items: center;
    min-height: 36px;
    padding: 8px 13px;
  }
}

.advanced-filters {
  display: grid;
  grid-template-columns:
    minmax(150px, 1fr)
    minmax(280px, 1.4fr)
    minmax(130px, 0.75fr)
    minmax(150px, 0.85fr)
    auto;
  gap: 10px;

  > * {
    min-width: 0;
  }

  .date-filter {
    width: 100%;
  }

  .apply-button {
    min-height: 40px;
    margin-left: 0;
  }
}

.mobile-filter-button {
  display: none;
}

.result-summary {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  min-height: 24px;

  strong {
    color: var(--xunji-text);
    font-size: 15px;
    font-weight: 650;
  }

  span {
    color: var(--xunji-text-muted);
    font-size: 12px;
  }
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(240px, 100%), 1fr));
  gap: 16px;
}

.pagination {
  margin-top: 8px;
  justify-content: center;
}

@media (max-width: 1180px) and (min-width: 721px) {
  .advanced-filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));

    .date-filter {
      grid-column: 1 / -1;
    }

    .apply-button {
      grid-column: 1 / -1;
      justify-self: end;
      min-width: 136px;
    }
  }
}

@media (max-width: 720px) {
  .page {
    gap: 16px;
  }

  .page-header {
    h1 {
      margin-top: 3px;
      font-size: 21px;
    }

    p {
      display: none;
    }
  }

  .filter-card :deep(.el-card__body) {
    gap: 12px;
    padding: 14px;
  }

  .mode-toggle {
    width: 100%;

    :deep(.el-radio-button) {
      width: 50%;
    }

    :deep(.el-radio-button__inner) {
      width: 100%;
      min-height: 44px;
      padding: 12px 10px;
    }
  }

  .filter-card :deep(.el-input--large .el-input__wrapper) {
    min-height: 44px;
  }

  .filter-card :deep(.el-input-group__append .el-button) {
    min-width: 64px;
    min-height: 44px;
  }

  .chips {
    gap: 6px;

    :deep(.el-check-tag) {
      min-height: 44px;
      padding: 10px 12px;
    }
  }

  .desktop-filters {
    display: none;
  }

  .mobile-filter-button {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    width: 100%;
    min-height: 44px;
    margin-left: 0;

    :deep(> span) {
      flex: 1;
      width: 100%;
    }

    .filter-count {
      margin-left: auto;
      color: var(--xunji-primary);
      font-size: 12px;
      font-weight: 600;
    }
  }

  .pagination {
    max-width: 100%;

    :deep(.el-pager li),
    :deep(.btn-prev),
    :deep(.btn-next) {
      min-width: 32px;
      margin: 0 2px;
    }
  }
}

:global(.mobile-filter-drawer) {
  max-width: 100vw;
  border-radius: 16px 16px 0 0;
}

:global(.mobile-filter-drawer .el-drawer__header) {
  min-height: 56px;
  margin-bottom: 0;
  padding: 16px 18px 10px;
  color: var(--xunji-text);
  font-weight: 700;
}

:global(.mobile-filter-drawer .el-drawer__close-btn) {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  margin: -10px -10px -10px 0;
}

:global(.mobile-filter-drawer .el-drawer__body) {
  min-width: 0;
  padding: 0 18px 12px;
  overflow-x: hidden;
}

:global(.mobile-filter-drawer .drawer-description) {
  margin: 0 0 16px;
  color: var(--xunji-text-muted);
  font-size: 12px;
  line-height: 1.5;
}

:global(.mobile-filter-drawer .el-form-item) {
  margin-bottom: 17px;
}

:global(.mobile-filter-drawer .el-form-item__label) {
  padding-bottom: 6px;
  color: var(--xunji-text);
  font-weight: 600;
}

:global(.mobile-filter-drawer .el-input),
:global(.mobile-filter-drawer .el-select),
:global(.mobile-filter-drawer .el-date-editor) {
  width: 100%;
  min-width: 0;
}

:global(.mobile-filter-drawer .el-input__wrapper),
:global(.mobile-filter-drawer .el-select__wrapper),
:global(.mobile-filter-drawer .el-date-editor) {
  min-height: 44px;
}

:global(.mobile-filter-drawer .el-range-input) {
  min-width: 0;
}

:global(.mobile-filter-drawer .el-drawer__footer) {
  padding: 10px 18px calc(12px + env(safe-area-inset-bottom));
  border-top: 1px solid var(--xunji-border);
}

:global(.mobile-filter-drawer .drawer-actions) {
  display: grid;
  grid-template-columns: 0.8fr 1.2fr;
  gap: 10px;
}

:global(.mobile-filter-drawer .drawer-actions .el-button) {
  min-height: 44px;
  margin-left: 0;
}
</style>
