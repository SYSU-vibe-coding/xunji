import { describe, expect, it } from 'vitest';
import { ErrorCode, isConflictApiError } from '@xunji/shared';

import { isAuthErrorCode, resolveApiBaseUrl } from './http';

describe('API base URL', () => {
  it('uses an absolute build-time URL and falls back to the nginx proxy path', () => {
    expect(resolveApiBaseUrl('https://api.example.test/api/v1')).toBe(
      'https://api.example.test/api/v1',
    );
    expect(resolveApiBaseUrl(undefined)).toBe('/api/v1');
    expect(resolveApiBaseUrl('')).toBe('/api/v1');
  });
});

describe('auth error classification', () => {
  it('clears sessions only for invalid or disabled credentials', () => {
    expect(isAuthErrorCode(ErrorCode.UNAUTHORIZED)).toBe(true);
    expect(isAuthErrorCode(ErrorCode.USER_DISABLED)).toBe(true);
    expect(isAuthErrorCode(ErrorCode.FORBIDDEN)).toBe(false);
    expect(isAuthErrorCode(-1)).toBe(false);
  });
});

describe('conflict error classification', () => {
  it('recognizes stale status and review writes without coupling to an app ApiError class', () => {
    expect(isConflictApiError({ code: ErrorCode.ITEM_CLOSED })).toBe(true);
    expect(isConflictApiError({ code: ErrorCode.CLAIM_INVALID_STATE })).toBe(true);
    expect(isConflictApiError({ code: ErrorCode.REVIEW_STATE_CHANGED })).toBe(true);
    expect(isConflictApiError({ code: ErrorCode.PARAM_ERROR })).toBe(false);
    expect(isConflictApiError(null)).toBe(false);
  });
});
