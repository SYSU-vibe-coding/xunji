<script setup lang="ts">
import { computed } from 'vue';
import { Clock, Location, Lock, Picture as PictureIcon } from '@element-plus/icons-vue';
import {
  type FoundItemSummary,
  type LostItemSummary,
  categoryLabels,
} from '@xunji/shared';

import StatusTag from './StatusTag.vue';
import { shortDateTime } from '@/utils/format';

type Kind = 'found' | 'lost';

const props = defineProps<{
  kind: Kind;
  item: FoundItemSummary | LostItemSummary;
  hideStatus?: boolean;
  showReview?: boolean;
}>();

defineEmits<{ open: [id: string, kind: Kind] }>();

const isFound = computed(() => props.kind === 'found');
const found = computed(() => (isFound.value ? (props.item as FoundItemSummary) : null));
const lost = computed(() => (isFound.value ? null : (props.item as LostItemSummary)));

const location = computed(() =>
  isFound.value ? found.value!.foundLocation : lost.value!.lostLocation,
);
const time = computed(() =>
  isFound.value ? shortDateTime(found.value!.foundTime) : shortDateTime(lost.value!.lostTimeStart),
);
const isSensitive = computed(() => isFound.value && Boolean(found.value?.isSensitive));
const cover = computed(() => props.item.coverImageUrl);
const detailLabel = computed(
  () => `查看${isFound.value ? '招领' : '失物'}信息：${props.item.itemName}`,
);
</script>

<template>
  <button
    type="button"
    class="item-card"
    :aria-label="detailLabel"
    @click="$emit('open', item.id, kind)"
  >
    <span class="cover">
      <img v-if="cover" :src="cover" :alt="item.itemName" />
      <span v-else class="cover-fallback">
        <el-icon :size="36">
          <Lock v-if="isSensitive" />
          <PictureIcon v-else />
        </el-icon>
        <span v-if="isSensitive">敏感原图已隐藏</span>
      </span>
      <span class="badges">
        <el-tag size="small" effect="dark" round>{{ categoryLabels[item.category] }}</el-tag>
        <StatusTag
          v-if="!hideStatus"
          :variant="kind"
          :value="item.status"
        />
        <StatusTag v-if="showReview" variant="review" :value="item.reviewStatus" />
      </span>
    </span>
    <span class="body">
      <span class="title" role="heading" aria-level="3">{{ item.itemName }}</span>
      <span class="desc">{{ item.description || '暂无描述' }}</span>
      <span v-if="showReview && item.reviewComment" class="review-comment">
        审核意见：{{ item.reviewComment }}
      </span>
      <span class="meta">
        <span>
          <el-icon aria-hidden="true"><Location /></el-icon>
          <span>{{ location }}</span>
        </span>
        <span>
          <el-icon aria-hidden="true"><Clock /></el-icon>
          <span>{{ time }}</span>
        </span>
      </span>
    </span>
  </button>
</template>

<style scoped lang="scss">
.item-card {
  width: 100%;
  height: 100%;
  padding: 0;
  appearance: none;
  border: 1px solid var(--xunji-border);
  border-radius: var(--xunji-radius);
  background: var(--xunji-surface);
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  overflow: hidden;

  &:focus-visible {
    outline: 3px solid rgba(13, 79, 79, 0.2);
    outline-offset: 2px;
  }

  @media (hover: hover) {
    &:hover {
      transform: translateY(-2px);
      box-shadow: var(--xunji-shadow);
    }
  }

  &:active {
    transform: translateY(1px);
  }
}

.cover {
  display: block;
  position: relative;
  aspect-ratio: 16 / 10;
  background: #edf5f4;
  overflow: hidden;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .cover-fallback {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    color: var(--xunji-text-muted);
    font-size: 12px;
  }

  .badges {
    position: absolute;
    top: 10px;
    left: 10px;
    display: flex;
    gap: 6px;
  }
}

.body {
  display: block;
  padding: 14px 16px 16px;

  .title {
    display: block;
    margin: 0 0 6px;
    font-size: 15px;
    font-weight: 600;
    color: var(--xunji-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .desc {
    display: -webkit-box;
    margin: 0 0 10px;
    color: var(--xunji-text-muted);
    font-size: 13px;
    line-height: 1.5;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .review-comment {
    display: block;
    margin: -4px 0 10px;
    padding: 7px 9px;
    border-radius: 7px;
    background: var(--el-color-warning-light-9);
    color: var(--el-color-warning-dark-2);
    font-size: 12px;
    line-height: 1.45;
  }

  .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 7px 14px;
    color: var(--xunji-text-muted);
    font-size: 12px;

    > span {
      display: inline-flex;
      align-items: center;
      min-width: 0;
      gap: 5px;

      > span {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .el-icon {
      flex: 0 0 auto;
      color: var(--xunji-primary);
    }
  }
}
</style>
