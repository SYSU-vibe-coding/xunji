import type {
  AnnouncementStatus,
  CertStatus,
  ClaimReviewStatus,
  ContactPreference,
  CreditReasonCode,
  CustodyType,
  FoundItemStatus,
  HandoverMethod,
  ItemCategory,
  LostItemStatus,
  MatchStatus,
  NoticeType,
  ReportHandleStatus,
  ReportTargetType,
  ReviewStatus,
  UserRole,
  UserStatus,
  VerifyLevel,
} from './enums';

export const categoryLabels: Record<ItemCategory, string> = {
  CERT: '证件',
  ELECTRONIC: '电子设备',
  DAILY_USE: '生活用品',
  BOOK: '书籍文具',
  OTHER: '其他',
};

export const lostStatusLabels: Record<LostItemStatus, string> = {
  SEARCHING: '寻物中',
  FOUND: '已找回',
  CLOSED: '已关闭',
};

export const foundStatusLabels: Record<FoundItemStatus, string> = {
  PENDING: '待认领',
  CLAIMING: '认领中',
  RETURNED: '已归还',
  CLOSED: '已关闭',
};

export const matchStatusLabels: Record<MatchStatus, string> = {
  NEW: '新匹配',
  READ: '已查看',
  CLAIMED: '已认领',
  EXPIRED: '已过期',
};

export const reviewStatusLabels: Record<ReviewStatus, string> = {
  PENDING: '待审批',
  APPROVED: '已通过',
  REJECTED: '已驳回',
};

export const certStatusLabels: Record<CertStatus, string> = {
  UNVERIFIED: '未认证',
  PENDING: '认证中',
  APPROVED: '已认证',
  REJECTED: '认证驳回',
};

export const userRoleLabels: Record<UserRole, string> = {
  USER: '普通用户',
  STAFF: '后勤/安保',
  ADMIN: '管理员',
};

export const userStatusLabels: Record<UserStatus, string> = {
  ACTIVE: '可用',
  DISABLED: '已禁用',
  CANCELLED: '已注销',
};

export const custodyTypeLabels: Record<CustodyType, string> = {
  SELF: '自行保管',
  SECURITY: '保卫处',
  OFFICE: '院系办公室',
};

export const contactPreferenceLabels: Record<ContactPreference, string> = {
  IN_APP: '站内联系',
  PHONE: '电话联系',
};

export const claimStatusLabels: Record<ClaimReviewStatus, string> = {
  PENDING: '待审核',
  ANSWER_PASSED: '问答通过',
  PROOF_PENDING: '待补凭证',
  APPROVED: '可交接',
  REJECTED: '已驳回',
  APPEALING: '申诉中',
  HANDED_OVER: '已交接',
  TERMINATED: '已终止',
};

export const verifyLevelLabels: Record<VerifyLevel, string> = {
  LEVEL_1: '问答验证',
  LEVEL_2: '问答 + 凭证',
  LEVEL_3: '线下核对',
};

export const handoverMethodLabels: Record<HandoverMethod, string> = {
  MEETUP: '当面交接',
  PICKUP_POINT: '指定地点',
};

export const noticeTypeLabels: Record<NoticeType, string> = {
  MATCH_RECOMMEND: '匹配推荐',
  CLAIM_REQUEST: '认领申请',
  CLAIM_REVIEW: '认领审核',
  HANDOVER_REMINDER: '交接提醒',
  CREDIT_CHANGED: '积分变动',
  SYSTEM_ANNOUNCEMENT: '系统公告',
};

export const reportTargetTypeLabels: Record<ReportTargetType, string> = {
  LOST_ITEM: '失物信息',
  FOUND_ITEM: '招领信息',
  CLAIM_REQUEST: '认领申请',
};

export const reportStatusLabels: Record<ReportHandleStatus, string> = {
  PENDING: '待处理',
  PROCESSING: '处理中',
  CLOSED: '已关闭',
  REJECTED: '已驳回',
};

export const announcementStatusLabels: Record<AnnouncementStatus, string> = {
  DRAFT: '草稿',
  PUBLISHED: '已发布',
  OFFLINE: '已下线',
};

export const creditReasonLabels: Record<CreditReasonCode, string> = {
  HANDOVER_SUCCESS: '完成交接',
  FOUND_ITEM_PUBLISHED: '发布招领',
  PEER_GOOD_REVIEW: '好评',
  CERT_APPROVED: '实名认证通过',
  CLAIM_REJECTED_NO_APPEAL: '认领被驳回未申诉',
  FRAUD_CLAIM_CONFIRMED: '冒领被核实',
  FAKE_PUBLISH_CONFIRMED: '虚假发布被核实',
  CLAIM_TIMEOUT_NO_REPLY: '认领超时未响应',
};
