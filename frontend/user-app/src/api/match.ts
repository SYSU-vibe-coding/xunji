import type {
  MatchQuery,
  MatchRecalculateRequest,
  MatchRecalculateResponse,
  MatchDetail,
  MatchSummary,
  PageData,
} from '@xunji/shared';

import { http, request } from './http';

export function listMatches(query: MatchQuery) {
  return http.get<PageData<MatchSummary>>('/matches', query as unknown as Record<string, unknown>);
}

export function getMatch(id: string) {
  return http.get<MatchDetail>(`/matches/${id}`);
}

export function recalculateMatch(payload: MatchRecalculateRequest) {
  return request<MatchRecalculateResponse>({
    url: '/matches/recalculate',
    method: 'POST',
    data: payload,
    timeout: 60_000,
  });
}

export function recalculateCompletedMessage(result: MatchRecalculateResponse): string {
  return `重算完成，已更新 ${result.matchedCount} 条匹配`;
}
