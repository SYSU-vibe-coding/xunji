import type { BizType, NoticeType, NotificationPriority } from '../enums';

export interface NotificationSummary {
  id: string;
  noticeType: NoticeType;
  title: string;
  content: string | null;
  isRead: boolean;
  relatedType: BizType | null;
  relatedId: string | null;
  priority: NotificationPriority;
  createdAt: string;
}

export interface NotificationQuery {
  pageNo?: number;
  pageSize?: number;
  isRead?: boolean;
  noticeType?: NoticeType;
}

export interface UnreadCountResponse {
  total: number;
  byType: Record<string, number>;
}

export interface ReadAllRequest {
  noticeType?: NoticeType;
}

export interface AnnouncementSummary {
  id: string;
  title: string;
  publishedAt: string;
}

export interface AnnouncementDetail extends AnnouncementSummary {
  content: string;
}
