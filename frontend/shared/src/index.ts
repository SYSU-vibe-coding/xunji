export type UserRole = 'USER' | 'STAFF' | 'ADMIN';
export type CertStatus = 'UNVERIFIED' | 'PENDING' | 'APPROVED' | 'REJECTED';
export type UserStatus = 'ACTIVE' | 'DISABLED' | 'CANCELLED';
export type ReviewStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

export type ItemCategory = 'CERT' | 'ELECTRONIC' | 'DAILY_USE' | 'BOOK' | 'OTHER';
export type LostItemStatus = 'SEARCHING' | 'FOUND' | 'CLOSED';
export type FoundItemStatus = 'PENDING' | 'CLAIMING' | 'RETURNED' | 'CLOSED';
export type CustodyType = 'SELF' | 'SECURITY' | 'OFFICE';
export type ContactPreference = 'IN_APP' | 'PHONE';
export type BizType = 'LOST' | 'FOUND' | 'CLAIM_PROOF' | 'CERT' | 'USER' | 'CLAIM' | 'REPORT' | 'ANNOUNCEMENT';

export type MatchStatus = 'NEW' | 'READ' | 'CLAIMED' | 'EXPIRED';
export type VerifyLevel = 'LEVEL_1' | 'LEVEL_2' | 'LEVEL_3' | 'FAST_TRACK';
export type ClaimReviewStatus =
  | 'PENDING'
  | 'ANSWER_PASSED'
  | 'PROOF_PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'APPEALING'
  | 'HANDED_OVER';
export type HandoverMethod = 'MEETUP' | 'PICKUP_POINT';

export type NoticeType =
  | 'MATCH_RECOMMEND'
  | 'CLAIM_REQUEST'
  | 'CLAIM_REVIEW'
  | 'HANDOVER_REMINDER'
  | 'CREDIT_CHANGED'
  | 'SYSTEM_ANNOUNCEMENT';
export type NotificationPriority = 'NORMAL' | 'HIGH';

export type ReportTargetType = 'LOST_ITEM' | 'FOUND_ITEM' | 'CLAIM_REQUEST' | 'USER';
export type ReportHandleStatus = 'PENDING' | 'PROCESSING' | 'CLOSED' | 'REJECTED';
export type AnnouncementStatus = 'DRAFT' | 'PUBLISHED' | 'OFFLINE';

export interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
  requestId: string;
  timestamp: string;
}

export interface PageData<T> {
  list: T[];
  pageNo: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface SmsCodeResponse {
  sent: boolean;
  expiresIn: number;
  debugCode?: string;
}

export interface LoginResponse {
  token: string;
  user: {
    id: string;
    nickname: string;
    avatarUrl: string | null;
    role: UserRole;
    certStatus: CertStatus;
    creditScore: number;
  };
}

export interface CurrentUser {
  id: string;
  phone: string;
  nickname: string;
  avatarUrl: string | null;
  role: UserRole;
  certStatus: CertStatus;
  campusId: string | null;
  realName: string | null;
  creditScore: number;
  status: UserStatus;
}

export interface LostItemSummary {
  id: string;
  userId: string;
  itemName: string;
  category: ItemCategory;
  description: string | null;
  lostTimeStart: string;
  lostTimeEnd: string;
  lostLocation: string;
  status: LostItemStatus;
  reviewStatus: ReviewStatus;
  coverImageUrl: string | null;
  createdAt: string;
  matchCount?: number;
  subscribeMatch?: boolean;
  imageUrls?: string[];
  updatedAt?: string;
}

export interface FoundItemSummary {
  id: string;
  userId: string;
  itemName: string;
  category: ItemCategory;
  description: string | null;
  foundTime: string;
  foundLocation: string;
  status: FoundItemStatus;
  reviewStatus: ReviewStatus;
  coverImageUrl: string | null;
  isSensitive: boolean;
  custodyType: CustodyType;
  contactPreference: ContactPreference;
  createdAt: string;
  hasActiveClaim?: boolean;
}

export interface MatchSummary {
  matchId: string;
  lostItemId: string;
  foundItemId: string;
  imageScore: number;
  textScore: number;
  locationScore: number;
  timeScore: number;
  totalScore: number;
  matchStatus: MatchStatus;
  counterpart: {
    id: string;
    itemName: string;
    category: ItemCategory;
    coverImageUrl: string | null;
    location: string;
    time: string;
  };
  createdAt: string;
  canClaim: boolean;
}

export interface ClaimSummary {
  id: string;
  foundItemId: string;
  itemName: string;
  verifyLevel: VerifyLevel;
  reviewStatus: ClaimReviewStatus;
  updatedAt: string;
  handoverLocation: string | null;
}

export interface NotificationSummary {
  id: string;
  noticeType: NoticeType;
  title: string;
  content: string;
  isRead: boolean;
  relatedType: BizType | null;
  relatedId: string | null;
  priority: NotificationPriority;
  createdAt: string;
}

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
  realName: string;
  documentImageUrl: string;
  reviewStatus: ReviewStatus;
  createdAt: string;
}

export interface ItemReviewRecord {
  id: string;
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
  reportedUserId: string;
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

export const claimStatusLabels: Record<ClaimReviewStatus, string> = {
  PENDING: '待审核',
  ANSWER_PASSED: '问答通过',
  PROOF_PENDING: '待补凭证',
  APPROVED: '可交接',
  REJECTED: '已驳回',
  APPEALING: '申诉中',
  HANDED_OVER: '已交接',
};

export const verifyLevelLabels: Record<VerifyLevel, string> = {
  LEVEL_1: '问答验证',
  LEVEL_2: '问答 + 凭证',
  LEVEL_3: '线下核对',
  FAST_TRACK: '证件快捷通道',
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

export const reportStatusLabels: Record<ReportHandleStatus, string> = {
  PENDING: '待处理',
  PROCESSING: '处理中',
  CLOSED: '已关闭',
  REJECTED: '已驳回',
};

export const noticeTypeLabels: Record<NoticeType, string> = {
  MATCH_RECOMMEND: '匹配推荐',
  CLAIM_REQUEST: '认领申请',
  CLAIM_REVIEW: '认领审核',
  HANDOVER_REMINDER: '交接提醒',
  CREDIT_CHANGED: '积分变动',
  SYSTEM_ANNOUNCEMENT: '系统公告',
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

export const demoUser: CurrentUser = {
  id: '01HW6J2Z9R7R6QW5S2A9V8K3NN',
  phone: '138****6028',
  nickname: '张同学',
  avatarUrl: null,
  role: 'USER',
  certStatus: 'APPROVED',
  campusId: '2022110842',
  realName: '张明',
  creditScore: 92,
  status: 'ACTIVE',
};

export const demoLostItems: LostItemSummary[] = [
  {
    id: '01HW7M0R3R4DN3A7E4KGMHQWA1',
    userId: demoUser.id,
    itemName: '白色 AirPods Pro',
    category: 'ELECTRONIC',
    description: '耳机盒外壳有一个浅灰色保护套，左耳机电量偏低。',
    lostTimeStart: '2026-04-27 18:20:00',
    lostTimeEnd: '2026-04-27 19:10:00',
    lostLocation: '图书馆二楼东侧自习区',
    status: 'SEARCHING',
    reviewStatus: 'APPROVED',
    coverImageUrl: 'https://images.unsplash.com/photo-1603351154351-5e2d0600bb77?auto=format&fit=crop&w=640&q=80',
    createdAt: '2026-04-27 19:25:00',
    matchCount: 3,
  },
  {
    id: '01HW7M0R3R4DN3A7E4KGMHQWA2',
    userId: demoUser.id,
    itemName: '数据结构教材',
    category: 'BOOK',
    description: '封面贴有蓝色便签，书内夹了一张课程表。',
    lostTimeStart: '2026-04-26 13:40:00',
    lostTimeEnd: '2026-04-26 15:00:00',
    lostLocation: '第一教学楼 A308',
    status: 'FOUND',
    reviewStatus: 'APPROVED',
    coverImageUrl: 'https://images.unsplash.com/photo-1512820790803-83ca734da794?auto=format&fit=crop&w=640&q=80',
    createdAt: '2026-04-26 16:10:00',
    matchCount: 1,
  },
];

export const demoFoundItems: FoundItemSummary[] = [
  {
    id: '01HW7M1DXR1N1SP72E4X0B7J21',
    userId: '01HW6J2Z9R7R6QW5S2A9V8K3Q0',
    itemName: '白色 AirPods Pro',
    category: 'ELECTRONIC',
    description: '在靠窗位置发现，耳机盒有浅灰保护套。',
    foundTime: '2026-04-27 18:55:00',
    foundLocation: '图书馆二楼东侧',
    status: 'PENDING',
    reviewStatus: 'APPROVED',
    coverImageUrl: 'https://images.unsplash.com/photo-1606741965429-8d76ff50bb2f?auto=format&fit=crop&w=640&q=80',
    isSensitive: false,
    custodyType: 'SELF',
    contactPreference: 'IN_APP',
    createdAt: '2026-04-27 19:02:00',
    hasActiveClaim: false,
  },
  {
    id: '01HW7M1DXR1N1SP72E4X0B7J22',
    userId: '01HW6J2Z9R7R6QW5S2A9V8K3Q1',
    itemName: '校园一卡通',
    category: 'CERT',
    description: '卡面已脱敏，仅保留院系和尾号线索。',
    foundTime: '2026-04-28 08:15:00',
    foundLocation: '南区食堂二楼',
    status: 'CLAIMING',
    reviewStatus: 'APPROVED',
    coverImageUrl: null,
    isSensitive: true,
    custodyType: 'SECURITY',
    contactPreference: 'IN_APP',
    createdAt: '2026-04-28 08:22:00',
    hasActiveClaim: true,
  },
  {
    id: '01HW7M1DXR1N1SP72E4X0B7J23',
    userId: '01HW6J2Z9R7R6QW5S2A9V8K3Q2',
    itemName: '黑色笔记本',
    category: 'BOOK',
    description: '封面写有实验记录，内页有绿色书签。',
    foundTime: '2026-04-28 10:40:00',
    foundLocation: '第一教学楼 A 座大厅',
    status: 'PENDING',
    reviewStatus: 'APPROVED',
    coverImageUrl: 'https://images.unsplash.com/photo-1531346878377-a5be20888e57?auto=format&fit=crop&w=640&q=80',
    isSensitive: false,
    custodyType: 'OFFICE',
    contactPreference: 'PHONE',
    createdAt: '2026-04-28 10:48:00',
    hasActiveClaim: false,
  },
  {
    id: '01HW7M1DXR1N1SP72E4X0B7J24',
    userId: '01HW6J2Z9R7R6QW5S2A9V8K3Q3',
    itemName: '蓝色雨伞',
    category: 'DAILY_USE',
    description: '折叠伞，伞柄处有磨损。',
    foundTime: '2026-04-27 20:10:00',
    foundLocation: '体育馆西门',
    status: 'RETURNED',
    reviewStatus: 'APPROVED',
    coverImageUrl: 'https://images.unsplash.com/photo-1515694346937-94d85e41e6f0?auto=format&fit=crop&w=640&q=80',
    isSensitive: false,
    custodyType: 'SELF',
    contactPreference: 'IN_APP',
    createdAt: '2026-04-27 20:20:00',
    hasActiveClaim: false,
  },
];

export const demoMatches: MatchSummary[] = [
  {
    matchId: '01HW7M4ZQ2W4EG9QCS0F7K7B11',
    lostItemId: demoLostItems[0].id,
    foundItemId: demoFoundItems[0].id,
    imageScore: 88.5,
    textScore: 82,
    locationScore: 96,
    timeScore: 91,
    totalScore: 87.6,
    matchStatus: 'NEW',
    counterpart: {
      id: demoFoundItems[0].id,
      itemName: demoFoundItems[0].itemName,
      category: demoFoundItems[0].category,
      coverImageUrl: demoFoundItems[0].coverImageUrl,
      location: demoFoundItems[0].foundLocation,
      time: demoFoundItems[0].foundTime,
    },
    createdAt: '2026-04-27 19:03:00',
    canClaim: true,
  },
  {
    matchId: '01HW7M4ZQ2W4EG9QCS0F7K7B12',
    lostItemId: demoLostItems[0].id,
    foundItemId: demoFoundItems[1].id,
    imageScore: 34,
    textScore: 41,
    locationScore: 70,
    timeScore: 60,
    totalScore: 45.2,
    matchStatus: 'READ',
    counterpart: {
      id: demoFoundItems[1].id,
      itemName: demoFoundItems[1].itemName,
      category: demoFoundItems[1].category,
      coverImageUrl: demoFoundItems[1].coverImageUrl,
      location: demoFoundItems[1].foundLocation,
      time: demoFoundItems[1].foundTime,
    },
    createdAt: '2026-04-28 08:24:00',
    canClaim: false,
  },
];

export const demoClaims: ClaimSummary[] = [
  {
    id: '01HW7M62ZAGTT8W4F1VAN4XER1',
    foundItemId: demoFoundItems[0].id,
    itemName: '白色 AirPods Pro',
    verifyLevel: 'LEVEL_2',
    reviewStatus: 'APPROVED',
    updatedAt: '2026-04-28 11:20:00',
    handoverLocation: '图书馆一楼服务台',
  },
  {
    id: '01HW7M62ZAGTT8W4F1VAN4XER2',
    foundItemId: demoFoundItems[1].id,
    itemName: '校园一卡通',
    verifyLevel: 'FAST_TRACK',
    reviewStatus: 'HANDED_OVER',
    updatedAt: '2026-04-28 09:15:00',
    handoverLocation: '保卫处证件窗口',
  },
];

export const demoNotifications: NotificationSummary[] = [
  {
    id: '01HW7M75E2DCSF22MCG0HK4W01',
    noticeType: 'MATCH_RECOMMEND',
    title: '发现高匹配线索',
    content: '你的白色 AirPods Pro 与图书馆二楼招领信息匹配度为 87.6%。',
    isRead: false,
    relatedType: 'FOUND',
    relatedId: demoFoundItems[0].id,
    priority: 'HIGH',
    createdAt: '2026-04-27 19:03:00',
  },
  {
    id: '01HW7M75E2DCSF22MCG0HK4W02',
    noticeType: 'CLAIM_REVIEW',
    title: '认领审核已通过',
    content: '请在约定时间前往图书馆一楼服务台完成交接。',
    isRead: true,
    relatedType: 'CLAIM',
    relatedId: demoClaims[0].id,
    priority: 'NORMAL',
    createdAt: '2026-04-28 11:20:00',
  },
  {
    id: '01HW7M75E2DCSF22MCG0HK4W03',
    noticeType: 'CREDIT_CHANGED',
    title: '信誉积分 +5',
    content: '完成一次有效交接，系统已记录积分流水。',
    isRead: false,
    relatedType: 'CLAIM',
    relatedId: demoClaims[1].id,
    priority: 'NORMAL',
    createdAt: '2026-04-28 09:16:00',
  },
];

export const demoDashboardStats: DashboardStats = {
  totalUsers: 2864,
  totalLost: 418,
  totalFound: 563,
  handedOverCount: 279,
  recoveryRate: 64.8,
  avgHandleHours: 18.6,
  pendingCertifications: 12,
  pendingReports: 7,
};

export const demoCertifications: CertificationReview[] = [
  {
    id: '01HW7M9ZWPQSP3G9H7C9AKQ601',
    userId: '01HW6J2Z9R7R6QW5S2A9V8K3C1',
    nickname: '林同学',
    campusId: '2023110628',
    realName: '林悦',
    documentImageUrl: 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=640&q=80',
    reviewStatus: 'PENDING',
    createdAt: '2026-04-28 09:42:00',
  },
  {
    id: '01HW7M9ZWPQSP3G9H7C9AKQ602',
    userId: '01HW6J2Z9R7R6QW5S2A9V8K3C2',
    nickname: '吴老师',
    campusId: 'STAFF0198',
    realName: '吴珩',
    documentImageUrl: 'https://images.unsplash.com/photo-1573496130141-209d200cebd8?auto=format&fit=crop&w=640&q=80',
    reviewStatus: 'PENDING',
    createdAt: '2026-04-28 10:18:00',
  },
];

export const demoItemReviews: ItemReviewRecord[] = [
  {
    id: demoFoundItems[1].id,
    bizType: 'FOUND',
    itemName: demoFoundItems[1].itemName,
    category: demoFoundItems[1].category,
    location: demoFoundItems[1].foundLocation,
    ownerNickname: '陈同学',
    status: demoFoundItems[1].status,
    reviewStatus: demoFoundItems[1].reviewStatus,
    isSensitive: true,
    reportCount: 0,
    createdAt: demoFoundItems[1].createdAt,
  },
  {
    id: demoLostItems[0].id,
    bizType: 'LOST',
    itemName: demoLostItems[0].itemName,
    category: demoLostItems[0].category,
    location: demoLostItems[0].lostLocation,
    ownerNickname: demoUser.nickname,
    status: demoLostItems[0].status,
    reviewStatus: demoLostItems[0].reviewStatus,
    isSensitive: false,
    reportCount: 1,
    createdAt: demoLostItems[0].createdAt,
  },
];

export const demoReports: ReportRecord[] = [
  {
    id: '01HW7MC3Z1VQ6ESY0WRWTFZ901',
    reporterId: '01HW6J2Z9R7R6QW5S2A9V8K3R1',
    reportedUserId: '01HW6J2Z9R7R6QW5S2A9V8K3R2',
    targetType: 'CLAIM_REQUEST',
    targetId: demoClaims[0].id,
    reason: '疑似冒领',
    description: '对方无法说出耳机保护套颜色，但仍要求线下交接。',
    handleStatus: 'PENDING',
    createdAt: '2026-04-28 12:04:00',
  },
  {
    id: '01HW7MC3Z1VQ6ESY0WRWTFZ902',
    reporterId: '01HW6J2Z9R7R6QW5S2A9V8K3R3',
    reportedUserId: '01HW6J2Z9R7R6QW5S2A9V8K3R4',
    targetType: 'FOUND_ITEM',
    targetId: demoFoundItems[2].id,
    reason: '信息不完整',
    description: '发布地点过于模糊，且图片与描述不一致。',
    handleStatus: 'PROCESSING',
    createdAt: '2026-04-27 17:30:00',
  },
];

export const demoAdminUsers: AdminUserRecord[] = [
  {
    id: demoUser.id,
    phone: demoUser.phone,
    nickname: demoUser.nickname,
    role: 'USER',
    certStatus: 'APPROVED',
    creditScore: demoUser.creditScore,
    status: 'ACTIVE',
    lastActiveAt: '2026-04-28 12:16:00',
  },
  {
    id: '01HW6J2Z9R7R6QW5S2A9V8K3U2',
    phone: '139****8126',
    nickname: '陈同学',
    role: 'USER',
    certStatus: 'APPROVED',
    creditScore: 67,
    status: 'ACTIVE',
    lastActiveAt: '2026-04-28 11:08:00',
  },
  {
    id: '01HW6J2Z9R7R6QW5S2A9V8K3U3',
    phone: '137****2481',
    nickname: '测试账号',
    role: 'USER',
    certStatus: 'REJECTED',
    creditScore: 28,
    status: 'DISABLED',
    lastActiveAt: '2026-04-26 16:28:00',
  },
];

export const categoryOptions = Object.entries(categoryLabels).map(([value, label]) => ({ value: value as ItemCategory, label }));
export const custodyOptions = Object.entries(custodyTypeLabels).map(([value, label]) => ({ value: value as CustodyType, label }));
export const contactOptions = Object.entries(contactPreferenceLabels).map(([value, label]) => ({
  value: value as ContactPreference,
  label,
}));

export function scoreTone(score: number): 'weak' | 'normal' | 'strong' {
  if (score >= 90) return 'strong';
  if (score >= 70) return 'normal';
  return 'weak';
}

export function formatPercent(value: number): string {
  return `${value.toFixed(value % 1 === 0 ? 0 : 1)}%`;
}

export function timeShort(value: string): string {
  const [, time = value] = value.split(' ');
  return time.slice(0, 5);
}

export function dateShort(value: string): string {
  const [date = value] = value.split(' ');
  return date.slice(5).replace('-', '/');
}
