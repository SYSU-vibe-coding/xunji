import type { MatchQuery, MatchSummary, PageData } from '@xunji/shared';
import { ErrorCode } from '@xunji/shared';

import { ApiError, http } from './http';

const EMPTY_PAGE: PageData<MatchSummary> = { list: [], pageNo: 1, pageSize: 0, total: 0, totalPages: 0 };

/**
 * Match 模块后端 router 暂未实现。
 * 调用失败（404 / NOT_FOUND）时统一降级返回空页，避免阻断用户端流程。
 * 后端 ready 后无需改动调用方。
 */
async function safeCall<T>(promise: Promise<T>, fallback: T): Promise<T> {
  try {
    return await promise;
  } catch (err) {
    if (err instanceof ApiError && (err.code === 404 || err.code === ErrorCode.NOT_FOUND)) {
      return fallback;
    }
    throw err;
  }
}

export function listMatches(query: MatchQuery = {}) {
  return safeCall(
    http.get<PageData<MatchSummary>>('/matches', query as Record<string, unknown>),
    EMPTY_PAGE,
  );
}

export function getMatch(id: string) {
  return safeCall(http.get<MatchSummary | null>(`/matches/${id}`), null);
}

export function recalculateMatch(payload: { lostItemId?: string; foundItemId?: string }) {
  return safeCall(http.post<{ taskId: string }>('/matches/recalculate', payload), { taskId: '' });
}
