import type { BizType, ItemCategory, MatchStatus } from '../enums';

export type MatchBizType = Extract<BizType, 'LOST' | 'FOUND'>;

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
  canClaim?: boolean;
}

export interface MatchDetail extends MatchSummary {
  canClaim: boolean;
  lostItem: Record<string, unknown>;
  foundItem: Record<string, unknown>;
}

export interface MatchQuery {
  bizType?: MatchBizType;
  bizId?: string;
  pageNo?: number;
  pageSize?: number;
  minScore?: number;
  status?: MatchStatus;
}

export interface MatchRecalculateRequest {
  bizType: MatchBizType;
  bizId: string;
}

export interface MatchRecalculateResponse {
  taskId: string;
  estimatedCount: number;
  status?: string;
}
