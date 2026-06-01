import type { LoginRequest, LoginResponse, UserProfile } from '@xunji/shared';

import { http } from './http';

/** 后台账号密码登录（与用户端走同一接口，但 role 必须为 ADMIN） */
export function loginAdmin(account: string, password: string) {
  return http.post<LoginResponse>('/auth/login', {
    loginType: 'PASSWORD',
    account,
    password,
  } satisfies LoginRequest);
}

export function getMyProfile() {
  return http.get<UserProfile>('/users/me');
}
