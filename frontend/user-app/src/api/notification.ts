import type {
  AnnouncementDetail,
  AnnouncementSummary,
  NotificationQuery,
  NotificationSummary,
  PageData,
  ReadAllRequest,
  UnreadCountResponse,
} from '@xunji/shared';

import { http } from './http';

export function listNotifications(query: NotificationQuery = {}) {
  return http.get<PageData<NotificationSummary>>(
    '/notifications',
    query as Record<string, unknown>,
  );
}

export function getUnreadCount() {
  return http.get<UnreadCountResponse>('/notifications/unread-count');
}

export function markNotificationRead(id: string) {
  return http.post<{ id: string; isRead: boolean }>(`/notifications/${id}/read`);
}

export function markAllNotificationsRead(payload: ReadAllRequest = {}) {
  return http.post<{ updated: number }>('/notifications/read-all', payload);
}

export function listAnnouncements(query: { pageNo?: number; pageSize?: number } = {}) {
  return http.get<PageData<AnnouncementSummary>>(
    '/announcements',
    query as Record<string, unknown>,
  );
}

export function getAnnouncement(id: string) {
  return http.get<AnnouncementDetail>(`/announcements/${id}`);
}
