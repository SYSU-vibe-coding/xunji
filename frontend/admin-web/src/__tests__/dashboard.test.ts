import { describe, expect, it } from 'vitest';

import { demoDashboardStats, reportStatusLabels, reviewStatusLabels } from '@xunji/shared';

describe('admin app shared contract', () => {
  it('keeps pending workload visible', () => {
    expect(demoDashboardStats.pendingCertifications).toBeGreaterThan(0);
    expect(demoDashboardStats.pendingReports).toBeGreaterThan(0);
  });

  it('uses documented review and report status labels', () => {
    expect(reviewStatusLabels.PENDING).toBe('待审批');
    expect(reportStatusLabels.PROCESSING).toBe('处理中');
  });
});
