import type {
  AdminUserQuery,
  AdminUserRecord,
  AnnouncementCreateRequest,
  AnnouncementCreateResponse,
  CertificationQuery,
  CertificationReview,
  DashboardStats,
  ItemReviewQuery,
  ItemReviewRecord,
  PageData,
  ReportHandleRequest,
  ReportQuery,
  ReportRecord,
  ReviewRequest,
  UserStatusRequest,
} from '@xunji/shared';

import { http } from './http';

export function getDashboard() {
  return http.get<DashboardStats>('/admin/dashboard');
}

// 认证
export function listCertifications(query: CertificationQuery = {}) {
  return http.get<PageData<CertificationReview>>(
    '/admin/certifications',
    query as Record<string, unknown>,
  );
}

export function reviewCertification(id: string, payload: ReviewRequest) {
  return http.post<{ id: string; reviewStatus: string }>(
    `/admin/certifications/${id}/review`,
    payload,
  );
}

// 内容审核
export function listItemReviews(query: ItemReviewQuery = {}) {
  return http.get<PageData<ItemReviewRecord>>(
    '/admin/items/review',
    query as Record<string, unknown>,
  );
}

export function reviewItem(bizType: 'LOST' | 'FOUND', id: string, payload: ReviewRequest) {
  return http.post<{ id: string; status: string; reviewStatus: string }>(
    `/admin/items/${bizType}/${id}/review`,
    payload,
  );
}

// 举报
export function listReports(query: ReportQuery = {}) {
  return http.get<PageData<ReportRecord>>('/admin/reports', query as Record<string, unknown>);
}

export function handleReport(id: string, payload: ReportHandleRequest) {
  return http.post<{ id: string; handleStatus: string }>(`/admin/reports/${id}/handle`, payload);
}

// 公告
export function createAnnouncement(payload: AnnouncementCreateRequest) {
  return http.post<AnnouncementCreateResponse>('/admin/announcements', payload);
}

// 用户管理
export function listAdminUsers(query: AdminUserQuery = {}) {
  return http.get<PageData<AdminUserRecord>>('/admin/users', query as Record<string, unknown>);
}

export function changeUserStatus(id: string, payload: UserStatusRequest) {
  return http.post<{ id: string; status: string }>(`/admin/users/${id}/status`, payload);
}
