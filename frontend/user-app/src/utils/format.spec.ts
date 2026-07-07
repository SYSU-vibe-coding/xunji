import { describe, expect, it } from 'vitest';

import { formatPercent, getInitial, shortDateTime, toBackendDateTime } from './format';

describe('user format utils', () => {
  it('formats backend date-time values for compact display', () => {
    expect(shortDateTime('2026-05-25 14:30:59')).toBe('05/25 14:30');
    expect(shortDateTime(null)).toBe('—');
  });

  it('formats percentages without noisy decimals', () => {
    expect(formatPercent(80)).toBe('80%');
    expect(formatPercent(66.6)).toBe('66.6%');
    expect(formatPercent(Number.NaN)).toBe('—');
  });

  it('builds backend date-time strings from Date objects', () => {
    expect(toBackendDateTime(new Date(2026, 4, 25, 9, 8, 7))).toBe('2026-05-25 09:08:07');
  });

  it('uses the first visible character as avatar initial', () => {
    expect(getInitial(' 寻迹同学 ')).toBe('寻');
    expect(getInitial('', '同')).toBe('同');
  });
});
