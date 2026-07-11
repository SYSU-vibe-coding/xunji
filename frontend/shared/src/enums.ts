/**
 * 与后端 docs/architecture/enums.md 对齐的字面量类型。
 * 任何变更必须先改文档再改这里。
 */

export type UserRole = 'USER' | 'STAFF' | 'ADMIN';
export type CertStatus = 'UNVERIFIED' | 'PENDING' | 'APPROVED' | 'REJECTED';
export type UserStatus = 'ACTIVE' | 'DISABLED' | 'CANCELLED';
export type ReviewStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

export type ItemCategory = 'CERT' | 'ELECTRONIC' | 'DAILY_USE' | 'BOOK' | 'OTHER';
export type LostItemStatus = 'SEARCHING' | 'FOUND' | 'CLOSED';
export type FoundItemStatus = 'PENDING' | 'CLAIMING' | 'RETURNED' | 'CLOSED';
export type CustodyType = 'SELF' | 'SECURITY' | 'OFFICE';
export type ContactPreference = 'IN_APP' | 'PHONE';

/** 业务对象类型，用于通知/日志/上传场景 */
export type BizType =
  | 'LOST'
  | 'FOUND'
  | 'CLAIM_PROOF'
  | 'CERT'
  | 'USER'
  | 'CLAIM'
  | 'MATCH'
  | 'REPORT'
  | 'ANNOUNCEMENT';

/** /files/upload 当前接受的业务类型，不等同于所有业务对象类型。 */
export type UploadBizType = Extract<BizType, 'LOST' | 'FOUND' | 'CLAIM_PROOF' | 'CERT' | 'USER'>;

export type MatchStatus = 'NEW' | 'READ' | 'CLAIMED' | 'EXPIRED';
export type VerifyLevel = 'LEVEL_1' | 'LEVEL_2' | 'LEVEL_3';

export type ClaimReviewStatus =
  | 'PENDING'
  | 'ANSWER_PASSED'
  | 'PROOF_PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'APPEALING'
  | 'HANDED_OVER'
  | 'TERMINATED';

export type HandoverMethod = 'MEETUP' | 'PICKUP_POINT';
export type HandoverRole = 'OWNER' | 'FINDER';
export type ClaimMyRole = 'CLAIMANT' | 'FINDER';
export type ReviewAction = 'APPROVE' | 'REJECT';
export type ReportAction = 'VALID' | 'INVALID';

export type NoticeType =
  | 'MATCH_RECOMMEND'
  | 'CLAIM_REQUEST'
  | 'CLAIM_REVIEW'
  | 'HANDOVER_REMINDER'
  | 'CREDIT_CHANGED'
  | 'SYSTEM_ANNOUNCEMENT';

export type NotificationPriority = 'NORMAL' | 'HIGH';

export type ReportTargetType = 'LOST_ITEM' | 'FOUND_ITEM' | 'CLAIM_REQUEST';
export type ReportHandleStatus = 'PENDING' | 'PROCESSING' | 'CLOSED' | 'REJECTED';
export type AnnouncementStatus = 'DRAFT' | 'PUBLISHED' | 'OFFLINE';

export type CreditReasonCode =
  | 'HANDOVER_SUCCESS'
  | 'FOUND_ITEM_PUBLISHED'
  | 'PEER_GOOD_REVIEW'
  | 'CERT_APPROVED'
  | 'CLAIM_REJECTED_NO_APPEAL'
  | 'FRAUD_CLAIM_CONFIRMED'
  | 'FAKE_PUBLISH_CONFIRMED'
  | 'CLAIM_TIMEOUT_NO_REPLY';

export type SortBy = 'CREATED_DESC' | 'CREATED_ASC' | 'EVENT_DESC' | 'EVENT_ASC';
export type LoginType = 'PHONE_CODE' | 'PASSWORD';

/** 后端响应码（节选最常用，详见 backend/app/common/errors.py） */
export const ErrorCode = {
  SUCCESS: 0,
  PARAM_ERROR: 40001,
  UNAUTHORIZED: 40002,
  FORBIDDEN: 40003,
  NOT_FOUND: 40004,
  INVALID_STATE: 40005,
  UPLOAD_FAILED: 40006,
  DUPLICATE_SUBMIT: 40008,
  PHONE_REGISTERED: 41001,
  SMS_CODE_INVALID: 41002,
  CERT_INCOMPLETE: 41003,
  CERT_PENDING: 41004,
  USER_DISABLED: 41005,
  ITEM_NOT_FOUND: 42001,
  ITEM_CLOSED: 42002,
  SENSITIVE_UNAUTHORIZED: 42005,
  MATCH_NOT_FOUND: 43001,
  MATCH_CLAIMED: 43002,
  CLAIM_DUPLICATE: 44001,
  CLAIM_NOT_FOUND: 44002,
  CLAIM_INVALID_STATE: 44003,
  APPEAL_DUPLICATE: 44007,
  REPORT_DUPLICATE: 47002,
  REVIEW_STATE_CHANGED: 48001,
} as const;

export type ErrorCodeValue = (typeof ErrorCode)[keyof typeof ErrorCode];

const CONFLICT_ERROR_CODES = new Set<number>([
  ErrorCode.INVALID_STATE,
  ErrorCode.DUPLICATE_SUBMIT,
  ErrorCode.CERT_PENDING,
  ErrorCode.ITEM_CLOSED,
  ErrorCode.MATCH_CLAIMED,
  ErrorCode.CLAIM_DUPLICATE,
  ErrorCode.CLAIM_INVALID_STATE,
  ErrorCode.APPEAL_DUPLICATE,
  ErrorCode.REPORT_DUPLICATE,
  ErrorCode.REVIEW_STATE_CHANGED,
]);

/** 识别需要放弃旧操作并刷新服务端状态的并发/状态机冲突。 */
export function isConflictApiError(error: unknown): error is { code: number; message?: string } {
  if (!error || typeof error !== 'object' || !('code' in error)) return false;
  return CONFLICT_ERROR_CODES.has((error as { code: number }).code);
}
