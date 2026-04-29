import type {
  ClaimMyRole,
  ClaimReviewStatus,
  HandoverMethod,
  HandoverRole,
  ReviewAction,
  VerifyLevel,
} from '../enums';

export interface ClaimAnswerInput {
  questionId: string;
  answerText: string;
}

export interface CreateClaimRequest {
  matchId?: string | null;
  foundItemId: string;
  answers?: ClaimAnswerInput[];
  proofImageUrls?: string[];
}

export interface CreateClaimResponse {
  id: string;
  verifyLevel: VerifyLevel;
  reviewStatus: ClaimReviewStatus;
}

export interface ClaimMyQuery {
  role?: ClaimMyRole;
  reviewStatus?: ClaimReviewStatus;
  pageNo?: number;
  pageSize?: number;
}

export interface ClaimSummary {
  id: string;
  foundItemId: string;
  itemName: string;
  verifyLevel: VerifyLevel;
  reviewStatus: ClaimReviewStatus;
  updatedAt: string;
}

export interface ClaimAnswerOutput {
  questionId: string;
  questionText: string;
  answerText: string;
  matchScore: number;
}

export interface HandoverDetail {
  id: string;
  method: HandoverMethod;
  handoverLocation: string;
  handoverTime: string;
  ownerConfirmed: boolean;
  finderConfirmed: boolean;
  completedAt: string | null;
  createdAt: string;
}

export interface ClaimDetail {
  id: string;
  matchId: string | null;
  foundItemId: string;
  claimantId: string;
  verifyLevel: VerifyLevel;
  reviewStatus: ClaimReviewStatus;
  rejectReason: string | null;
  answers: ClaimAnswerOutput[];
  proofImageUrls: string[];
  proofText: string | null;
  handover: HandoverDetail | null;
  claimedAt: string;
  updatedAt: string;
}

export interface ClaimReviewRequest {
  action: ReviewAction;
  comment?: string;
}

export interface ClaimProofsRequest {
  proofImageUrls: string[];
  proofText?: string;
}

export interface ClaimAppealRequest {
  reason: string;
}

export interface CreateHandoverRequest {
  method: HandoverMethod;
  handoverLocation: string;
  handoverTime: string;
}

export interface CreateHandoverResponse {
  handoverId: string;
}

export interface ConfirmHandoverRequest {
  role: HandoverRole;
}
