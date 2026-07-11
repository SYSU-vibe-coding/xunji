import { describe, expect, it } from 'vitest';

import { recalculateCompletedMessage } from './match';

describe('match API copy', () => {
  it('describes synchronous recalculation as completed rather than queued', () => {
    const message = recalculateCompletedMessage({ status: 'COMPLETED', matchedCount: 3 });

    expect(message).toBe('重算完成，已更新 3 条匹配');
    expect(message).not.toContain('提交');
    expect(message).not.toContain('任务');
  });
});
