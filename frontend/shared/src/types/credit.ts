import type { BizType, CreditReasonCode } from '../enums';

export interface CreditLogItem {
  id: string;
  userId: string;
  deltaScore: number;
  reasonCode: CreditReasonCode;
  reasonText: string | null;
  bizType: BizType;
  bizId: string;
  createdAt: string;
}

export interface CreditLogQuery {
  pageNo?: number;
  pageSize?: number;
  reasonCode?: CreditReasonCode;
}
