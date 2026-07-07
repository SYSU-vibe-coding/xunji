import type {
  MatchQuery,
  MatchRecalculateRequest,
  MatchRecalculateResponse,
  MatchDetail,
  MatchSummary,
  PageData,
} from '@xunji/shared';

import { http } from './http';

export function listMatches(query: MatchQuery) {
  return http.get<PageData<MatchSummary>>('/matches', query as unknown as Record<string, unknown>);
}

export function getMatch(id: string) {
  return http.get<MatchDetail>(`/matches/${id}`);
}

export function recalculateMatch(payload: MatchRecalculateRequest) {
  return http.post<MatchRecalculateResponse>('/matches/recalculate', payload);
}
