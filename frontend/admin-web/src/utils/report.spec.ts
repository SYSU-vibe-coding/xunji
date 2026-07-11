import { describe, expect, it } from 'vitest';
import type { ReportRecord, ReportTargetType } from '@xunji/shared';

import { buildReportHandlePayload, isSupportedReportTargetType, reportTargetRoute } from './report';

function report(targetType: ReportTargetType): ReportRecord {
  return {
    id: 'report-1',
    reporterId: 'reporter-1',
    reportedUserId: 'user-1',
    targetType,
    targetId: 'target-1',
    reason: '虚假信息',
    description: '',
    handleStatus: 'PENDING',
    handleResult: null,
    handlerId: null,
    createdAt: '2026-07-11T00:00:00Z',
  };
}

describe('report handling', () => {
  it.each(['LOST_ITEM', 'FOUND_ITEM'] as const)(
    'uses the fake-publish penalty for %s',
    (targetType) => {
      expect(buildReportHandlePayload(report(targetType), 'VALID', '确认虚假发布')).toEqual({
        action: 'VALID',
        result: '确认虚假发布',
        creditDelta: -20,
        reasonCode: 'FAKE_PUBLISH_CONFIRMED',
      });
    },
  );

  it('removes all penalty fields for an invalid report', () => {
    expect(buildReportHandlePayload(report('LOST_ITEM'), 'INVALID', ' 证据不足 ')).toEqual({
      action: 'INVALID',
      result: '证据不足',
    });
  });

  it('passes exact target IDs without pretending a user ID is a keyword', () => {
    expect(reportTargetRoute(report('FOUND_ITEM'))).toEqual({
      path: '/reviews',
      query: { bizType: 'FOUND', targetId: 'target-1' },
    });
    expect(reportTargetRoute(report('CLAIM_REQUEST'))).toEqual({
      path: '/claim-appeals',
      query: { targetId: 'target-1' },
    });
  });

  it('rejects legacy USER targets from the operable frontend contract', () => {
    expect(isSupportedReportTargetType('USER')).toBe(false);
    expect(isSupportedReportTargetType('CLAIM_REQUEST')).toBe(true);
  });
});
