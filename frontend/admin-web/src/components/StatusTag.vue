<script setup lang="ts">
import { computed } from 'vue';
import type {
  CertStatus,
  ClaimReviewStatus,
  FoundItemStatus,
  LostItemStatus,
  ReportHandleStatus,
  ReviewStatus,
  UserStatus,
} from '@xunji/shared';
import {
  certStatusLabels,
  claimStatusLabels,
  foundStatusLabels,
  lostStatusLabels,
  reportStatusLabels,
  reviewStatusLabels,
  userStatusLabels,
} from '@xunji/shared';

type Variant = 'lost' | 'found' | 'claim' | 'review' | 'cert' | 'report' | 'user';

const props = withDefaults(
  defineProps<{ variant: Variant; value: string; size?: 'small' | 'default' | 'large' }>(),
  { size: 'small' },
);

const labelMap: Record<Variant, Record<string, string>> = {
  lost: lostStatusLabels as Record<LostItemStatus, string>,
  found: foundStatusLabels as Record<FoundItemStatus, string>,
  claim: claimStatusLabels as Record<ClaimReviewStatus, string>,
  review: reviewStatusLabels as Record<ReviewStatus, string>,
  cert: certStatusLabels as Record<CertStatus, string>,
  report: reportStatusLabels as Record<ReportHandleStatus, string>,
  user: userStatusLabels as Record<UserStatus, string>,
};

const TONE: Record<Variant, Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'info'>> = {
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
  report: { PENDING: 'warning', PROCESSING: 'primary', CLOSED: 'success', REJECTED: 'danger' },
  user: { ACTIVE: 'success', DISABLED: 'danger', CANCELLED: 'info' },
};

const text = computed(() => labelMap[props.variant]?.[props.value] ?? props.value);
const tone = computed(() => TONE[props.variant]?.[props.value] ?? 'info');
</script>

<template>
  <el-tag :type="tone" :size="size" effect="light" round>{{ text }}</el-tag>
</template>
