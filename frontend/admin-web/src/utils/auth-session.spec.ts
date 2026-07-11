import { describe, expect, it } from 'vitest';

import { hasAdminRouteAccess } from './auth-session';

describe('admin route session gate', () => {
  it('does not admit an initialized token without a loaded admin profile', () => {
    expect(hasAdminRouteAccess('disabled-session-token', null, true)).toBe(false);
    expect(hasAdminRouteAccess('token', { role: 'USER' }, true)).toBe(false);
  });

  it('admits only an initialized admin profile and token', () => {
    expect(hasAdminRouteAccess('token', { role: 'ADMIN' }, false)).toBe(false);
    expect(hasAdminRouteAccess('token', { role: 'ADMIN' }, true)).toBe(true);
  });
});
