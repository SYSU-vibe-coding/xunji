import type { ItemCategory, MatchStatus } from '../enums';

/**
 * Match 模块后端 router 暂未实现（见 docs/architecture/matching-rules.md）。
 * 前端先行定义类型与 API 路径占位。
 */
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

export interface MatchQuery {
  pageNo?: number;
  pageSize?: number;
  lostItemId?: string;
  foundItemId?: string;
  matchStatus?: MatchStatus;
}
