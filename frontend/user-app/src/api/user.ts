import type {
  CertificationDetail,
  CertificationRequest,
  UpdateProfileRequest,
  UserProfile,
} from '@xunji/shared';

import { http } from './http';

export function getMyProfile() {
  return http.get<UserProfile>('/users/me');
}

export function updateMyProfile(payload: UpdateProfileRequest) {
  return http.put<UserProfile>('/users/me', payload);
}

export function submitCertification(payload: CertificationRequest) {
  return http.post<CertificationDetail>('/users/me/certification', payload);
}

export function getMyCertification() {
  return http.get<CertificationDetail | null>('/users/me/certification');
}

export function cancelMyAccount() {
  return http.post<{ id: string; status: string }>('/users/me/cancel');
}
