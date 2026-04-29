import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  SmsCodeRequest,
  SmsCodeResponse,
} from '@xunji/shared';

import { http } from './http';

export function sendSmsCode(payload: SmsCodeRequest) {
  return http.post<SmsCodeResponse>('/auth/sms-code', payload);
}

export function loginByPassword(phone: string, password: string) {
  return http.post<LoginResponse>('/auth/login', {
    loginType: 'PASSWORD',
    phone,
    password,
  } satisfies LoginRequest);
}

export function loginByAccountPassword(account: string, password: string) {
  return http.post<LoginResponse>('/auth/login', {
    loginType: 'PASSWORD',
    account,
    password,
  } satisfies LoginRequest);
}

export function loginBySmsCode(phone: string, code: string) {
  return http.post<LoginResponse>('/auth/login', {
    loginType: 'PHONE_CODE',
    phone,
    code,
  } satisfies LoginRequest);
}

export function register(payload: RegisterRequest) {
  return http.post<LoginResponse>('/auth/register', payload);
}
