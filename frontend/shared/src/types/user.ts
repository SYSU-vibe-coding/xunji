import type { CertStatus, LoginType, ReviewStatus, UserRole, UserStatus } from '../enums';

export interface SmsCodeRequest {
  phone: string;
}

export interface SmsCodeResponse {
  sent: boolean;
  expiresIn: number;
  /** 仅本地开发返回，正式环境为空 */
  debugCode: string;
}

export interface LoginRequest {
  loginType: LoginType;
  phone?: string;
  account?: string;
  code?: string;
  password?: string;
}

export interface RegisterRequest {
  phone: string;
  code: string;
  nickname: string;
  password: string;
}

export interface LoginUserData {
  id: string;
  nickname: string;
  avatarUrl: string | null;
  role: UserRole;
  certStatus: CertStatus;
  creditScore: number;
}

export interface LoginResponse {
  token: string;
  user: LoginUserData;
}

export interface UserProfile {
  id: string;
  /** 已脱敏的手机号 */
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

export interface UpdateProfileRequest {
  nickname?: string;
  avatarUrl?: string;
}

export interface CertificationRequest {
  campusId: string;
  realName: string;
  documentImageUrl: string;
}

export interface CertificationDetail {
  id: string;
  campusId: string;
  realName: string | null;
  documentImageUrl: string;
  reviewStatus: ReviewStatus;
  reviewComment: string | null;
  reviewedAt: string | null;
  createdAt: string;
}
