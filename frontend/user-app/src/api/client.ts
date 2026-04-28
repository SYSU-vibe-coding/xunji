import type {
  ApiEnvelope,
  ClaimSummary,
  CurrentUser,
  FoundItemSummary,
  LoginResponse,
  LostItemSummary,
  NotificationSummary,
  PageData,
  SmsCodeResponse,
} from '@xunji/shared';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code?: number,
  ) {
    super(message);
  }
}

export function getStoredToken(): string {
  return localStorage.getItem('xunji-user-token') ?? '';
}

export function setStoredToken(token: string) {
  localStorage.setItem('xunji-user-token', token);
}

export function clearStoredToken() {
  localStorage.removeItem('xunji-user-token');
}

export async function requestJson<T>(
  path: string,
  init: RequestInit & { token?: string; skipAuth?: boolean } = {},
): Promise<T> {
  const token = init.token ?? getStoredToken();
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(!init.skipAuth && token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const envelope = (await response.json()) as ApiEnvelope<T>;
  if (envelope.code !== 0) {
    throw new ApiError(envelope.message, envelope.code);
  }
  return envelope.data;
}

export const userApiRoutes = {
  login: '/auth/login',
  register: '/auth/register',
  me: '/users/me',
  lostItems: '/lost-items',
  foundItems: '/found-items',
  matches: '/matches',
  claims: '/claims',
  notifications: '/notifications',
} as const;

export function sendSmsCode(phone: string): Promise<SmsCodeResponse> {
  return requestJson<SmsCodeResponse>(userApiRoutes.login.replace('/login', '/sms-code'), {
    method: 'POST',
    body: JSON.stringify({ phone }),
    skipAuth: true,
  });
}

export async function loginWithPhoneCode(phone: string, code: string): Promise<LoginResponse> {
  const data = await requestJson<LoginResponse>(userApiRoutes.login, {
    method: 'POST',
    body: JSON.stringify({ loginType: 'PHONE_CODE', phone, code }),
    skipAuth: true,
  });
  setStoredToken(data.token);
  return data;
}

export async function loginWithPassword(phone: string, password: string): Promise<LoginResponse> {
  const data = await requestJson<LoginResponse>(userApiRoutes.login, {
    method: 'POST',
    body: JSON.stringify({ loginType: 'PASSWORD', phone, password }),
    skipAuth: true,
  });
  setStoredToken(data.token);
  return data;
}

export async function registerWithPhone(payload: {
  phone: string;
  code: string;
  password: string;
  nickname: string;
}): Promise<LoginResponse> {
  const data = await requestJson<LoginResponse>(userApiRoutes.register, {
    method: 'POST',
    body: JSON.stringify(payload),
    skipAuth: true,
  });
  setStoredToken(data.token);
  return data;
}

export function getMyProfile(): Promise<CurrentUser> {
  return requestJson<CurrentUser>(userApiRoutes.me);
}

export function listFoundItems(params = 'pageNo=1&pageSize=20'): Promise<PageData<FoundItemSummary>> {
  return requestJson<PageData<FoundItemSummary>>(`${userApiRoutes.foundItems}?${params}`);
}

export function listLostItems(params = 'pageNo=1&pageSize=20'): Promise<PageData<LostItemSummary>> {
  return requestJson<PageData<LostItemSummary>>(`${userApiRoutes.lostItems}?${params}`);
}

export function getLostItem(id: string): Promise<LostItemSummary> {
  return requestJson<LostItemSummary>(`${userApiRoutes.lostItems}/${id}`);
}

export async function listMyClaims(params = 'pageNo=1&pageSize=20'): Promise<PageData<ClaimSummary>> {
  const data = await requestJson<PageData<ClaimSummary>>(`${userApiRoutes.claims}/my?${params}`);
  return {
    ...data,
    list: data.list.map((item) => ({
      ...item,
      handoverLocation: item.handoverLocation ?? null,
    })),
  };
}

export function listNotifications(params = 'pageNo=1&pageSize=20'): Promise<PageData<NotificationSummary>> {
  return requestJson<PageData<NotificationSummary>>(`${userApiRoutes.notifications}?${params}`);
}

export function createLostItem(payload: unknown): Promise<{ id: string; status: string }> {
  return requestJson<{ id: string; status: string }>(userApiRoutes.lostItems, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateLostItem(payload: { id: string; data: unknown }): Promise<{ id: string; status: string; reviewStatus: string }> {
  return requestJson<{ id: string; status: string; reviewStatus: string }>(`${userApiRoutes.lostItems}/${payload.id}`, {
    method: 'PUT',
    body: JSON.stringify(payload.data),
  });
}

export function deleteLostItem(id: string): Promise<{ id: string; status: string }> {
  return requestJson<{ id: string; status: string }>(`${userApiRoutes.lostItems}/${id}`, {
    method: 'DELETE',
  });
}

export function createFoundItem(payload: unknown): Promise<{ id: string; status: string; isSensitive: boolean }> {
  return requestJson<{ id: string; status: string; isSensitive: boolean }>(userApiRoutes.foundItems, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
