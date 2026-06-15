import { describe, expect, it, vi } from 'vitest';

import { getInitial, relativeTime, shortDateTime } from './format';

describe('admin format utils', () => {
  it('formats backend date-time values for table cells', () => {
    expect(shortDateTime('2026-05-25 14:30:59')).toBe('05/25 14:30');
    expect(shortDateTime(undefined)).toBe('—');
  });

  it('formats recent relative times', () => {
    vi.setSystemTime(new Date('2026-05-25T14:30:00'));

    expect(relativeTime('2026-05-25 14:29:30')).toBe('刚刚');
    expect(relativeTime('2026-05-25 14:00:00')).toBe('30 分钟前');
  });

  it('uses a fallback initial for empty names', () => {
    expect(getInitial(' 管理员 ')).toBe('管');
    expect(getInitial('', '管')).toBe('管');
  });
});
