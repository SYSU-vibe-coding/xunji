import { describe, expect, it } from 'vitest';
import { ErrorCode } from '@xunji/shared';

import {
  ApiError,
  isAuthErrorCode,
  isUnauthorizedApiError,
  isUnauthorizedErrorCode,
  resolveApiBaseUrl,
} from './http';

describe('API base URL', () => {
  it('accepts an absolute build-time URL and falls back to the proxy path', () => {
    expect(resolveApiBaseUrl('http://localhost:8080/api/v1')).toBe(
      'http://localhost:8080/api/v1',
    );
    expect(resolveApiBaseUrl(undefined)).toBe('/api/v1');
    expect(resolveApiBaseUrl('')).toBe('/api/v1');
  });
});

describe('auth error classification', () => {
  it('expires sessions for UNAUTHORIZED and USER_DISABLED', () => {
    expect(isUnauthorizedErrorCode(ErrorCode.UNAUTHORIZED)).toBe(true);
    expect(isUnauthorizedErrorCode(ErrorCode.USER_DISABLED)).toBe(true);
    expect(isUnauthorizedApiError(new ApiError(ErrorCode.USER_DISABLED, 'disabled'))).toBe(true);
    expect(isUnauthorizedErrorCode(ErrorCode.FORBIDDEN)).toBe(false);
    expect(isUnauthorizedErrorCode(48002)).toBe(false);
  });

  it('still recognizes forbidden responses as auth-related errors', () => {
    expect(isAuthErrorCode(ErrorCode.USER_DISABLED)).toBe(true);
    expect(isAuthErrorCode(ErrorCode.FORBIDDEN)).toBe(true);
    expect(isAuthErrorCode(48002)).toBe(true);
  });
});
