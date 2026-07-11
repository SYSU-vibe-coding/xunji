import type { ReportHandleRequest, ReportRecord, ReportTargetType } from '@xunji/shared';
import type { RouteLocationRaw } from 'vue-router';

interface ReportPenalty {
  creditDelta: number;
  reasonCode: string;
  result: string;
}

const REPORT_PENALTIES: Partial<Record<ReportTargetType, ReportPenalty>> = {
  LOST_ITEM: {
    creditDelta: -20,
    reasonCode: 'FAKE_PUBLISH_CONFIRMED',
    result: '举报有效，确认该失物信息为虚假发布',
  },
  FOUND_ITEM: {
    creditDelta: -20,
    reasonCode: 'FAKE_PUBLISH_CONFIRMED',
    result: '举报有效，确认该招领信息为虚假发布',
  },
  CLAIM_REQUEST: {
    creditDelta: -30,
    reasonCode: 'FRAUD_CLAIM_CONFIRMED',
    result: '举报有效，确认该认领请求存在冒领行为',
  },
};

export function isSupportedReportTargetType(value: unknown): value is ReportTargetType {
  return value === 'LOST_ITEM' || value === 'FOUND_ITEM' || value === 'CLAIM_REQUEST';
}

export function reportPenalty(targetType: ReportTargetType): ReportPenalty | null {
  return REPORT_PENALTIES[targetType] ?? null;
}

export function buildReportHandlePayload(
  record: ReportRecord,
  action: 'VALID' | 'INVALID',
  result: string,
): ReportHandleRequest {
  const payload: ReportHandleRequest = { action, result: result.trim() };
  const penalty = action === 'VALID' ? reportPenalty(record.targetType) : null;
  if (penalty) {
    payload.creditDelta = penalty.creditDelta;
    payload.reasonCode = penalty.reasonCode;
  }
  return payload;
}

export function reportTargetRoute(record: ReportRecord): RouteLocationRaw | null {
  if (record.targetType === 'LOST_ITEM' || record.targetType === 'FOUND_ITEM') {
    return {
      path: '/reviews',
      query: {
        bizType: record.targetType === 'LOST_ITEM' ? 'LOST' : 'FOUND',
        targetId: record.targetId,
      },
    };
  }
  if (record.targetType === 'CLAIM_REQUEST') {
    return { path: '/claim-appeals', query: { targetId: record.targetId } };
  }
  return null;
}
