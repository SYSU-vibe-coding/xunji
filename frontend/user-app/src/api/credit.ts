import type { CreditLogItem, CreditLogQuery, PageData } from '@xunji/shared';

import { http } from './http';

export function listMyCreditLogs(query: CreditLogQuery = {}) {
  return http.get<PageData<CreditLogItem>>('/users/me/credits', query as Record<string, unknown>);
}
