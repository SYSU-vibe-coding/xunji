import type {
  AdminUserRecord,
  ApiEnvelope,
  CertificationReview,
  DashboardStats,
  ItemReviewRecord,
  LoginResponse,
  PageData,
  ReportRecord,
} from '@xunji/shared';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

export class AdminApiError extends Error {
  constructor(
    message: string,
    readonly code?: number,
  ) {
    super(message);
  }
}

export function getStoredAdminToken(): string {
  return localStorage.getItem('xunji-admin-token') ?? '';
}

export function setStoredAdminToken(token: string) {
  localStorage.setItem('xunji-admin-token', token);
}

export function clearStoredAdminToken() {
  localStorage.removeItem('xunji-admin-token');
}

export async function adminRequestJson<T>(
  path: string,
  init: RequestInit & { token?: string; skipAuth?: boolean } = {},
): Promise<T> {
  const token = init.token ?? getStoredAdminToken();
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
    throw new AdminApiError(envelope.message, envelope.code);
  }
  return envelope.data;
}

export const adminApiRoutes = {
  dashboard: '/admin/dashboard',
  certifications: '/admin/certifications',
  itemReviews: '/admin/items/review',
  reports: '/admin/reports',
  announcements: '/admin/announcements',
  users: '/admin/users',
} as const;

export async function loginAdminWithPassword(account: string, password: string): Promise<LoginResponse> {
  const data = await adminRequestJson<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ loginType: 'PASSWORD', account, password }),
    skipAuth: true,
  });
  setStoredAdminToken(data.token);
  return data;
}

export function getDashboard(): Promise<DashboardStats> {
  return adminRequestJson<DashboardStats>(adminApiRoutes.dashboard);
}

export function listCertifications(): Promise<PageData<CertificationReview>> {
  return adminRequestJson<PageData<CertificationReview>>(`${adminApiRoutes.certifications}?pageNo=1&pageSize=20`);
}

export function listItemReviews(): Promise<PageData<ItemReviewRecord>> {
  return adminRequestJson<PageData<ItemReviewRecord>>(`${adminApiRoutes.itemReviews}?pageNo=1&pageSize=20`);
}

export function listReports(): Promise<PageData<ReportRecord>> {
  return adminRequestJson<PageData<ReportRecord>>(`${adminApiRoutes.reports}?pageNo=1&pageSize=20`);
}

export function listAdminUsers(keyword = ''): Promise<PageData<AdminUserRecord>> {
  const query = new URLSearchParams({ pageNo: '1', pageSize: '20' });
  if (keyword) query.set('keyword', keyword);
  return adminRequestJson<PageData<AdminUserRecord>>(`${adminApiRoutes.users}?${query.toString()}`);
}

export function createAnnouncement(payload: unknown): Promise<{ id: string; status: string }> {
  return adminRequestJson<{ id: string; status: string }>(adminApiRoutes.announcements, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function reviewCertification(
  id: string,
  payload: { action: 'APPROVE' | 'REJECT'; comment?: string },
): Promise<{ id: string; reviewStatus: string }> {
  return adminRequestJson<{ id: string; reviewStatus: string }>(`${adminApiRoutes.certifications}/${id}/review`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function reviewItem(
  bizType: 'LOST' | 'FOUND',
  id: string,
  payload: { action: 'APPROVE' | 'REJECT'; comment?: string },
): Promise<{ id: string; status: string }> {
  return adminRequestJson<{ id: string; status: string }>(`/admin/items/${bizType}/${id}/review`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function handleAdminReport(
  id: string,
  payload: { action: 'VALID' | 'INVALID'; result?: string; creditDelta?: number; reasonCode?: string },
): Promise<{ id: string; handleStatus: string }> {
  return adminRequestJson<{ id: string; handleStatus: string }>(`${adminApiRoutes.reports}/${id}/handle`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function changeAdminUserStatus(
  id: string,
  payload: { status: 'ACTIVE' | 'DISABLED' | 'CANCELLED'; reason?: string },
): Promise<{ id: string; status: string }> {
  return adminRequestJson<{ id: string; status: string }>(`${adminApiRoutes.users}/${id}/status`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
