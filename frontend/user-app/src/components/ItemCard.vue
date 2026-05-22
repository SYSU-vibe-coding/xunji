<script setup lang="ts">
import { computed } from 'vue';
import { Clock3, MapPin, ShieldCheck } from 'lucide-vue-next';

import {
  categoryLabels,
  dateShort,
  foundStatusLabels,
  lostStatusLabels,
  type FoundItemSummary,
  type LostItemSummary,
} from '@xunji/shared';

const props = defineProps<{
  kind: 'found' | 'lost';
  item: FoundItemSummary | LostItemSummary;
  compact?: boolean;
}>();

const location = computed(() =>
  props.kind === 'found' ? (props.item as FoundItemSummary).foundLocation : (props.item as LostItemSummary).lostLocation,
);

const statusLabel = computed(() =>
  props.kind === 'found'
    ? foundStatusLabels[(props.item as FoundItemSummary).status]
    : lostStatusLabels[(props.item as LostItemSummary).status],
);

const eventTime = computed(() =>
  props.kind === 'found' ? (props.item as FoundItemSummary).foundTime : (props.item as LostItemSummary).lostTimeStart,
);

const isSensitive = computed(() => props.kind === 'found' && (props.item as FoundItemSummary).isSensitive);
</script>

<template>
  <article class="item-card" :class="{ compact }">
    <div class="item-media" :class="{ sensitive: isSensitive }">
      <img v-if="item.coverImageUrl" :src="item.coverImageUrl" :alt="item.itemName" />
      <div v-else class="sensitive-mask">
        <ShieldCheck :size="30" />
        <span>敏感物品</span>
      </div>
      <span class="media-badge">{{ dateShort(eventTime) }}</span>
    </div>

    <div class="item-body">
      <div class="item-title-row">
        <h3>{{ item.itemName }}</h3>
        <span class="status-badge">{{ statusLabel }}</span>
      </div>

      <p class="item-description">{{ item.description }}</p>

      <div class="item-meta">
        <span><MapPin :size="15" />{{ location }}</span>
        <span><Clock3 :size="15" />{{ categoryLabels[item.category] }}</span>
      </div>
    </div>
  </article>
</template>
