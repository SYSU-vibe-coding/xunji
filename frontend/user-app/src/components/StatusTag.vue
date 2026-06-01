<script setup lang="ts">
import { computed } from 'vue';
import type {
  CertStatus,
  ClaimReviewStatus,
  FoundItemStatus,
  LostItemStatus,
  ReviewStatus,
} from '@xunji/shared';
import {
  certStatusLabels,
  claimStatusLabels,
  foundStatusLabels,
  lostStatusLabels,
  reviewStatusLabels,
} from '@xunji/shared';

type StatusVariant = 'lost' | 'found' | 'claim' | 'review' | 'cert';

const props = withDefaults(
  defineProps<{
    variant: StatusVariant;
    value: string;
    size?: 'small' | 'default' | 'large';
  }>(),
  { size: 'small' },
);

const labelMap: Record<StatusVariant, Record<string, string>> = {
  lost: lostStatusLabels as Record<LostItemStatus, string>,
  found: foundStatusLabels as Record<FoundItemStatus, string>,
  claim: claimStatusLabels as Record<ClaimReviewStatus, string>,
  review: reviewStatusLabels as Record<ReviewStatus, string>,
  cert: certStatusLabels as Record<CertStatus, string>,
};

const TONE: Record<StatusVariant, Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'info'>> = {
  lost: { SEARCHING: 'warning', FOUND: 'success', CLOSED: 'info' },
  found: { PENDING: 'warning', CLAIMING: 'primary', RETURNED: 'success', CLOSED: 'info' },
  claim: {
    PENDING: 'warning',
    ANSWER_PASSED: 'primary',
    PROOF_PENDING: 'warning',
    APPROVED: 'success',
    REJECTED: 'danger',
    APPEALING: 'warning',
    HANDED_OVER: 'success',
  },
  review: { PENDING: 'warning', APPROVED: 'success', REJECTED: 'danger' },
  cert: { UNVERIFIED: 'info', PENDING: 'warning', APPROVED: 'success', REJECTED: 'danger' },
};

const text = computed(() => labelMap[props.variant]?.[props.value] ?? props.value);
const tone = computed(() => TONE[props.variant]?.[props.value] ?? 'info');
</script>

<template>
  <el-tag :type="tone" :size="size" effect="light" round>
    {{ text }}
  </el-tag>
</template>
