import type {
  ChangeItemStatusRequest,
  CreateFoundItemRequest,
  CreateFoundItemResponse,
  CreateFoundItemsBatchRequest,
  CreateFoundItemsBatchResponse,
  CreateLostItemRequest,
  CreateLostItemResponse,
  FoundItemDetail,
  FoundItemQuery,
  FoundItemSummary,
  LostItemDetail,
  LostItemQuery,
  LostItemSummary,
  PageData,
  ReportItemRequest,
  ReportItemResponse,
  UpdateFoundItemRequest,
  UpdateLostItemRequest,
} from '@xunji/shared';

import { http } from './http';

// ---- Lost ----

export function createLostItem(payload: CreateLostItemRequest) {
  return http.post<CreateLostItemResponse>('/lost-items', payload);
}

export function listLostItems(query: LostItemQuery = {}) {
  return http.get<PageData<LostItemSummary>>('/lost-items', query as Record<string, unknown>);
}

export function listMyLostItems(query: LostItemQuery = {}) {
  return http.get<PageData<LostItemSummary>>('/me/lost-items', query as Record<string, unknown>);
}

export function getLostItem(id: string) {
  return http.get<LostItemDetail>(`/lost-items/${id}`);
}

export function updateLostItem(id: string, payload: UpdateLostItemRequest) {
  return http.put<{ id: string; status: string; reviewStatus: string }>(`/lost-items/${id}`, payload);
}

export function deleteLostItem(id: string) {
  return http.delete<{ id: string; status: string }>(`/lost-items/${id}`);
}

export function changeLostItemStatus(id: string, payload: ChangeItemStatusRequest) {
  return http.patch<{ id: string; status: string }>(`/lost-items/${id}/status`, payload);
}

// ---- Found ----

export function createFoundItem(payload: CreateFoundItemRequest) {
  return http.post<CreateFoundItemResponse>('/found-items', payload);
}

export function createFoundItemsBatch(payload: CreateFoundItemsBatchRequest) {
  return http.post<CreateFoundItemsBatchResponse>('/found-items/batch', payload);
}

export function listFoundItems(query: FoundItemQuery = {}) {
  return http.get<PageData<FoundItemSummary>>('/found-items', query as Record<string, unknown>);
}

export function listMyFoundItems(query: FoundItemQuery = {}) {
  return http.get<PageData<FoundItemSummary>>('/me/found-items', query as Record<string, unknown>);
}

export function getFoundItem(id: string) {
  return http.get<FoundItemDetail>(`/found-items/${id}`);
}

export function updateFoundItem(id: string, payload: UpdateFoundItemRequest) {
  return http.put<{ id: string; status: string; reviewStatus: string }>(`/found-items/${id}`, payload);
}

export function changeFoundItemStatus(id: string, payload: ChangeItemStatusRequest) {
  return http.patch<{ id: string; status: string }>(`/found-items/${id}/status`, payload);
}

export function reportItem(bizType: 'LOST' | 'FOUND', id: string, payload: ReportItemRequest) {
  return http.post<ReportItemResponse>('/reports', {
    targetType: bizType === 'LOST' ? 'LOST_ITEM' : 'FOUND_ITEM',
    targetId: id,
    ...payload,
  });
}
