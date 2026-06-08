import type {
  ContactPreference,
  CustodyType,
  FoundItemStatus,
  ItemCategory,
  LostItemStatus,
  ReviewStatus,
  SortBy,
} from '../enums';

// ---- Lost ----

export interface CreateLostItemRequest {
  itemName: string;
  category: ItemCategory;
  description?: string | null;
  lostTimeStart: string; // yyyy-MM-dd HH:mm:ss
  lostTimeEnd: string;
  lostLocation: string;
  subscribeMatch?: boolean;
  imageUrls?: string[];
}

export interface CreateLostItemResponse {
  id: string;
  status: LostItemStatus;
}

export type UpdateLostItemRequest = CreateLostItemRequest;

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
}

export interface LostItemDetail extends LostItemSummary {
  subscribeMatch: boolean;
  imageUrls: string[];
  /** 仅发布者可见 */
  matchCount: number | null;
  updatedAt: string;
}

export interface LostItemQuery {
  pageNo?: number;
  pageSize?: number;
  category?: ItemCategory;
  status?: LostItemStatus;
  keyword?: string;
  location?: string;
  sortBy?: SortBy;
  /** 默认 false：list 接口隐藏 FOUND/CLOSED；显式传 true 才返回历史 */
  includeClosed?: boolean;
}

// ---- Found ----

export interface VerifyQuestionInput {
  questionText: string;
  answerKeywords: string[];
}

export interface CreateFoundItemRequest {
  itemName: string;
  category: ItemCategory;
  description?: string | null;
  foundTime: string;
  foundLocation: string;
  custodyType: CustodyType;
  contactPreference: ContactPreference;
  imageUrls?: string[];
  verifyQuestions?: VerifyQuestionInput[];
}

export interface CreateFoundItemResponse {
  id: string;
  status: FoundItemStatus;
  isSensitive: boolean;
}

export interface CreateFoundItemsBatchRequest {
  items: CreateFoundItemRequest[];
}

export interface CreateFoundItemsBatchFailure {
  index: number;
  error: string;
}

export interface CreateFoundItemsBatchResponse {
  successIds: string[];
  failures: CreateFoundItemsBatchFailure[];
}

export interface FoundItemSummary {
  id: string;
  userId: string;
  itemName: string;
  category: ItemCategory;
  description: string | null;
  foundTime: string;
  foundLocation: string;
  isSensitive: boolean;
  custodyType: CustodyType;
  contactPreference: ContactPreference;
  status: FoundItemStatus;
  reviewStatus: ReviewStatus;
  coverImageUrl: string | null;
  createdAt: string;
}

export interface VerifyQuestionOutput {
  id: string;
  questionText: string;
}

export interface FoundItemDetail extends Omit<FoundItemSummary, 'coverImageUrl'> {
  imageUrls: string[];
  verifyQuestions: VerifyQuestionOutput[];
  hasActiveClaim: boolean;
  updatedAt: string;
}

export interface FoundItemQuery {
  pageNo?: number;
  pageSize?: number;
  category?: ItemCategory;
  status?: FoundItemStatus;
  keyword?: string;
  location?: string;
  isSensitive?: boolean;
  custodyType?: CustodyType;
  sortBy?: SortBy;
  /** 默认 false：list 接口隐藏 RETURNED/CLOSED；显式传 true 才返回历史 */
  includeClosed?: boolean;
}

// ---- Status & Upload ----

export interface ChangeItemStatusRequest {
  status: LostItemStatus | FoundItemStatus;
}

export interface FileUploadResponse {
  url: string;
  contentType: string;
  size: number;
  uploadedAt: string;
}
