import type {
  ClaimAppealRequest,
  ClaimDetail,
  ClaimMyQuery,
  ClaimProofsRequest,
  ClaimReviewRequest,
  ClaimSummary,
  ConfirmHandoverRequest,
  CreateClaimRequest,
  CreateClaimResponse,
  CreateHandoverRequest,
  CreateHandoverResponse,
  PageData,
} from '@xunji/shared';

import { http } from './http';

export function createClaim(payload: CreateClaimRequest) {
  return http.post<CreateClaimResponse>('/claims', payload);
}

export function listMyClaims(query: ClaimMyQuery = {}) {
  return http.get<PageData<ClaimSummary>>('/claims/my', query as Record<string, unknown>);
}

export function getClaim(id: string) {
  return http.get<ClaimDetail>(`/claims/${id}`);
}

export function reviewClaim(id: string, payload: ClaimReviewRequest) {
  return http.post<{ id: string; reviewStatus: string }>(`/claims/${id}/review`, payload);
}

export function submitClaimProofs(id: string, payload: ClaimProofsRequest) {
  return http.post<{ id: string; reviewStatus: string }>(`/claims/${id}/proofs`, payload);
}

export function appealClaim(id: string, payload: ClaimAppealRequest) {
  return http.post<{ id: string; reviewStatus: string }>(`/claims/${id}/appeal`, payload);
}

export function createHandover(id: string, payload: CreateHandoverRequest) {
  return http.post<CreateHandoverResponse>(`/claims/${id}/handover`, payload);
}

export function confirmHandover(id: string, payload: ConfirmHandoverRequest) {
  return http.post<{ id: string; reviewStatus: string }>(
    `/claims/${id}/handover/confirm`,
    payload,
  );
}
