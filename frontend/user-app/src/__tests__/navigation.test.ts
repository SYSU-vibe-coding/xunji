import { describe, expect, it } from 'vitest';

import { categoryLabels, demoFoundItems, scoreTone } from '@xunji/shared';

describe('user app shared contract', () => {
  it('uses documented enum values for categories', () => {
    expect(categoryLabels.CERT).toBe('证件');
    expect(demoFoundItems.every((item) => Object.prototype.hasOwnProperty.call(categoryLabels, item.category))).toBe(true);
  });

  it('marks high confidence matches as normal or strong', () => {
    expect(scoreTone(87.6)).toBe('normal');
    expect(scoreTone(92)).toBe('strong');
  });
});
