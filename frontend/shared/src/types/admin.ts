import type {
  AnnouncementStatus,
  CertStatus,
  ClaimReviewStatus,
  ClaimVerificationSource,
  ContactPreference,
  CustodyType,
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
  VerifyLevel,
} from '../enums';
import type { ClaimAnswerOutput, ClaimDetail } from './claim';
import type { VerifyQuestionOutput } from './item';

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
  reviewComment: string | null;
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
  reviewComment: string | null;
  isSensitive: boolean;
  reportCount: number;
  createdAt: string;
}

export interface AdminPartySummary {
  id: string;
  nickname: string;
  phone: string;
  status: UserStatus;
}

export interface ItemReviewDetail {
  id: string;
  userId: string;
  bizType: 'LOST' | 'FOUND';
  itemName: string;
  category: ItemCategory;
  description: string | null;
  lostTimeStart?: string;
  lostTimeEnd?: string;
  lostLocation?: string;
  foundTime?: string;
  foundLocation?: string;
  status: LostItemStatus | FoundItemStatus;
  reviewStatus: ReviewStatus;
  reviewComment: string | null;
  isSensitive?: boolean;
  imageUrls: string[];
  verifyQuestions?: VerifyQuestionOutput[];
  publisher: AdminPartySummary;
  createdAt: string;
  updatedAt: string;
}

export interface AdminClaimItemSummary {
  id: string;
  itemName: string;
  category: ItemCategory;
  description: string | null;
  foundTime: string;
  foundLocation: string;
  custodyType: CustodyType;
  contactPreference: ContactPreference;
  status: FoundItemStatus;
  reviewStatus: ReviewStatus;
}

export interface AdminClaimRecord {
  id: string;
  foundItemId: string;
  verifyLevel: VerifyLevel;
  reviewStatus: ClaimReviewStatus;
  verificationSource: ClaimVerificationSource;
  verificationDegraded: boolean;
  rejectReason: string | null;
  appealReason: string | null;
  claimant: AdminPartySummary;
  finder: AdminPartySummary;
  item: AdminClaimItemSummary;
  claimedAt: string;
  updatedAt: string;
}

export interface AdminClaimAnswerOutput extends ClaimAnswerOutput {
  referenceAnswers: string[];
}

export interface AdminClaimDetail extends Omit<ClaimDetail, 'answers'> {
  answers: AdminClaimAnswerOutput[];
  verificationSource: ClaimVerificationSource;
  verificationDegraded: boolean;
  claimant: AdminPartySummary;
  finder: AdminPartySummary;
  item: AdminClaimItemSummary;
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
  handleResult: string | null;
  handlerId: string | null;
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
  targetId?: string;
}

export interface AdminClaimQuery extends AdminPageQuery {
  reviewStatus?: ClaimReviewStatus;
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

export interface AnnouncementRecord {
  id: string;
  title: string;
  content: string;
  status: AnnouncementStatus;
  publishedBy: string | null;
  publishedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AnnouncementQuery extends AdminPageQuery {
  status?: AnnouncementStatus;
}

export type UserStatusRequest =
  | { status: 'DISABLED'; reason: string }
  | { status: 'ACTIVE'; reason?: string };

export interface MatchJobStatus {
  status: 'idle' | 'running' | 'stopping';
  intervalMinutes: number;
  currentJobId: string | null;
  totalPairs: number;
  processedPairs: number;
  writtenMatches: number;
  lastRunStartedAt: string | null;
  lastRunFinishedAt: string | null;
  lastRunWrittenMatches: number;
  lastError: string | null;
  nextRunAt: string | null;
}

export interface MatchRunResponse {
  jobId: string;
}

export interface MatchIntervalRequest {
  intervalMinutes: number;
}

export interface MatchIntervalResponse {
  intervalMinutes: number;
}

export interface OperationLogRecord {
  id: string;
  operatorId: string;
  operatorRole: string;
  bizType: string;
  bizId: string;
  action: string;
  detail: string | null;
  createdAt: string;
}

export interface OperationLogQuery extends AdminPageQuery {
  bizType?: string;
  action?: string;
  operatorRole?: string;
  keyword?: string;
}
