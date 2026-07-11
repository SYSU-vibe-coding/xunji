<script setup lang="ts">
import { computed } from 'vue';
import { Lock, Picture as PictureIcon } from '@element-plus/icons-vue';
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
</script>

<template>
  <el-card
    shadow="never"
    class="item-card"
    :body-style="{ padding: 0 }"
    @click="$emit('open', item.id, kind)"
  >
    <div class="cover">
      <img v-if="cover && !isSensitive" :src="cover" :alt="item.itemName" />
      <div v-else class="cover-fallback">
        <el-icon :size="36">
          <Lock v-if="isSensitive" />
          <PictureIcon v-else />
        </el-icon>
        <span v-if="isSensitive">敏感物品已脱敏</span>
      </div>
      <div class="badges">
        <el-tag size="small" effect="dark" round>{{ categoryLabels[item.category] }}</el-tag>
        <StatusTag
          v-if="!hideStatus"
          :variant="kind"
          :value="item.status"
        />
        <StatusTag v-if="showReview" variant="review" :value="item.reviewStatus" />
      </div>
    </div>
    <div class="body">
      <h3>{{ item.itemName }}</h3>
      <p class="desc">{{ item.description || '暂无描述' }}</p>
      <p v-if="showReview && item.reviewComment" class="review-comment">
        审核意见：{{ item.reviewComment }}
      </p>
      <div class="meta">
        <span>📍 {{ location }}</span>
        <span>🕒 {{ time }}</span>
      </div>
    </div>
  </el-card>
</template>

<style scoped lang="scss">
.item-card {
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  overflow: hidden;

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--xunji-shadow);
  }
}

.cover {
  position: relative;
  aspect-ratio: 16 / 10;
  background: linear-gradient(135deg, #ecfeff, #e0e7ff);
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
  padding: 14px 16px 16px;

  h3 {
    margin: 0 0 6px;
    font-size: 15px;
    font-weight: 600;
    color: var(--xunji-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .desc {
    margin: 0 0 10px;
    color: var(--xunji-text-muted);
    font-size: 13px;
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .review-comment {
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
    justify-content: space-between;
    color: var(--xunji-text-muted);
    font-size: 12px;
  }
}
</style>
