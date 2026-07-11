import { describe, expect, it } from 'vitest';

import {
  createLatestRequestGuard,
  lastPage,
  queryEnum,
  queryPositiveInt,
} from './admin-list';

describe('admin list helpers', () => {
  it('normalizes URL filters and pagination', () => {
    expect(queryEnum('PENDING', ['PENDING', 'APPROVED'] as const)).toBe('PENDING');
    expect(queryEnum('UNKNOWN', ['PENDING', 'APPROVED'] as const)).toBe('');
    expect(queryPositiveInt('3')).toBe(3);
    expect(queryPositiveInt('-1')).toBe(1);
    expect(lastPage(21, 10)).toBe(3);
    expect(lastPage(0, 10)).toBe(1);
  });

  it('allows only the latest request to commit', () => {
    const guard = createLatestRequestGuard();
    const first = guard.next();
    const second = guard.next();

    expect(guard.isLatest(first)).toBe(false);
    expect(guard.isLatest(second)).toBe(true);
  });
});
