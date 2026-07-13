import type {
  AdminUserQuery,
  AdminUserRecord,
  AdminClaimDetail,
  AdminClaimQuery,
  AdminClaimRecord,
  AnnouncementCreateRequest,
  AnnouncementCreateResponse,
  AnnouncementQuery,
  AnnouncementRecord,
  CertificationQuery,
  CertificationReview,
  DashboardStats,
  ItemReviewQuery,
  ItemReviewDetail,
  ItemReviewRecord,
  MatchIntervalRequest,
  MatchIntervalResponse,
  MatchJobStatus,
  MatchRunResponse,
  OperationLogQuery,
  OperationLogRecord,
  PageData,
  ReportHandleRequest,
  ReportQuery,
  ReportRecord,
  ReviewRequest,
  UserStatusRequest,
} from '@xunji/shared';

import { http } from './http';

type ItemBizType = 'LOST' | 'FOUND';
type ItemBizTypePath = 'lost' | 'found';

function toItemBizTypePath(bizType: ItemBizType): ItemBizTypePath {
  return bizType.toLowerCase() as ItemBizTypePath;
}

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

export function getItemReviewDetail(bizType: ItemBizType, id: string) {
  return http.get<ItemReviewDetail>(`/admin/items/${toItemBizTypePath(bizType)}/${id}`);
}

export function reviewItem(bizType: ItemBizType, id: string, payload: ReviewRequest) {
  return http.post<{ id: string; status: string; reviewStatus: string }>(
    `/admin/items/${toItemBizTypePath(bizType)}/${id}/review`,
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

// 认领治理
export function listAdminClaims(query: AdminClaimQuery = {}) {
  return http.get<PageData<AdminClaimRecord>>('/admin/claims', query as Record<string, unknown>);
}

export function getAdminClaimDetail(id: string) {
  return http.get<AdminClaimDetail>(`/admin/claims/${id}`);
}

export function reviewClaimAppeal(id: string, payload: ReviewRequest) {
  return http.post<{ id: string; reviewStatus: string }>(`/claims/${id}/review`, payload);
}

// 公告
export function createAnnouncement(payload: AnnouncementCreateRequest) {
  return http.post<AnnouncementCreateResponse>('/admin/announcements', payload);
}

export function listAnnouncements(query: AnnouncementQuery = {}) {
  return http.get<PageData<AnnouncementRecord>>(
    '/admin/announcements',
    query as Record<string, unknown>,
  );
}

export function publishAnnouncement(id: string) {
  return http.post<AnnouncementCreateResponse>(`/admin/announcements/${id}/publish`);
}

export function offlineAnnouncement(id: string) {
  return http.post<AnnouncementCreateResponse>(`/admin/announcements/${id}/offline`);
}

// 用户管理
export function listAdminUsers(query: AdminUserQuery = {}) {
  return http.get<PageData<AdminUserRecord>>('/admin/users', query as Record<string, unknown>);
}

export function changeUserStatus(id: string, payload: UserStatusRequest) {
  return http.post<{ id: string; status: string }>(`/admin/users/${id}/status`, payload);
}

// 匹配任务控制
export function getMatchStatus() {
  return http.get<MatchJobStatus>('/admin/matches/status');
}

export function triggerMatchRun() {
  return http.post<MatchRunResponse>('/admin/matches/run');
}

export function setMatchInterval(payload: MatchIntervalRequest) {
  return http.put<MatchIntervalResponse>('/admin/matches/interval', payload);
}

// 操作日志
export function listOperationLogs(query: OperationLogQuery = {}) {
  return http.get<PageData<OperationLogRecord>>(
    '/admin/operation-logs',
    query as Record<string, unknown>,
  );
}
