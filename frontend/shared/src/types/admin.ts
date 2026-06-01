import type {
  AnnouncementStatus,
  CertStatus,
  FoundItemStatus,
  ItemCategory,
  LostItemStatus,
  ReportAction,
  ReportHandleStatus,
  ReportTargetType,
  ReviewAction,
  ReviewStatus,
  UserRole,
  UserStatus,
} from '../enums';

export interface DashboardStats {
  totalUsers: number;
  totalLost: number;
  totalFound: number;
  handedOverCount: number;
  recoveryRate: number;
  avgHandleHours: number;
  pendingCertifications: number;
  pendingReports: number;
}

export interface CertificationReview {
  id: string;
  userId: string;
  nickname: string;
  campusId: string;
  realName: string | null;
  documentImageUrl: string;
  reviewStatus: ReviewStatus;
  createdAt: string;
}

export interface ItemReviewRecord {
  id: string;
  userId: string;
  bizType: 'LOST' | 'FOUND';
  itemName: string;
  category: ItemCategory;
  location: string;
  ownerNickname: string;
  status: LostItemStatus | FoundItemStatus;
  reviewStatus: ReviewStatus;
  isSensitive: boolean;
  reportCount: number;
  createdAt: string;
}

export interface ReportRecord {
  id: string;
  reporterId: string;
  reportedUserId: string | null;
  targetType: ReportTargetType;
  targetId: string;
  reason: string;
  description: string;
  handleStatus: ReportHandleStatus;
  createdAt: string;
}

export interface AdminUserRecord {
  id: string;
  phone: string;
  nickname: string;
  role: UserRole;
  certStatus: CertStatus;
  creditScore: number;
  status: UserStatus;
  createdAt?: string;
  lastActiveAt?: string;
}

export interface AdminPageQuery {
  pageNo?: number;
  pageSize?: number;
}

export interface CertificationQuery extends AdminPageQuery {
  reviewStatus?: ReviewStatus;
}

export interface ItemReviewQuery extends AdminPageQuery {
  bizType?: 'LOST' | 'FOUND';
}

export interface ReportQuery extends AdminPageQuery {
  handleStatus?: ReportHandleStatus;
  targetType?: ReportTargetType;
}

export interface AdminUserQuery extends AdminPageQuery {
  role?: UserRole;
  status?: UserStatus;
  keyword?: string;
}

export interface ReviewRequest {
  action: ReviewAction;
  comment?: string;
}

export interface ReportHandleRequest {
  action: ReportAction;
  result?: string;
  creditDelta?: number;
  reasonCode?: string;
}

export interface AnnouncementCreateRequest {
  title: string;
  content: string;
  publishNow?: boolean;
}

export interface AnnouncementCreateResponse {
  id: string;
  status: AnnouncementStatus;
}

export interface UserStatusRequest {
  status: UserStatus;
  reason?: string;
}
