import { describe, expect, it } from 'vitest';

import { isMobileNavActive, MOBILE_NAV_ORDER } from './navigation';

describe('mobile navigation', () => {
  it('keeps the publish action in the exact center of five slots', () => {
    expect(MOBILE_NAV_ORDER).toEqual([
      'home',
      'search',
      'publish',
      'notifications',
      'profile',
    ]);
    expect(MOBILE_NAV_ORDER[2]).toBe('publish');
  });

  it('treats announcement details as part of the message center', () => {
    expect(isMobileNavActive('notifications', '/notifications')).toBe(true);
    expect(isMobileNavActive('notifications', '/announcements/01TEST')).toBe(true);
    expect(isMobileNavActive('notifications', '/search')).toBe(false);
  });
});
