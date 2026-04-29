import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios';
import { ErrorCode, type ApiEnvelope } from '@xunji/shared';

export const TOKEN_STORAGE_KEY = 'xunji-admin-token';

export class ApiError extends Error {
  code: number;
  requestId?: string;

  constructor(code: number, message: string, requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.requestId = requestId;
  }
}

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    /* ignore */
  }
}

export function clearStoredToken(): void {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

const instance: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
});

instance.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getStoredToken();
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`);
  }
  return config;
});

let onUnauthorized: (() => void) | null = null;
export function registerUnauthorizedHandler(fn: () => void): void {
  onUnauthorized = fn;
}

export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  try {
    const response = await instance.request<ApiEnvelope<T>>(config);
    const envelope = response.data;
    if (envelope && typeof envelope === 'object' && 'code' in envelope) {
      if (envelope.code === ErrorCode.SUCCESS) {
        return envelope.data;
      }
      if (envelope.code === ErrorCode.UNAUTHORIZED || envelope.code === ErrorCode.FORBIDDEN) {
        clearStoredToken();
        onUnauthorized?.();
      }
      throw new ApiError(envelope.code, envelope.message || '请求失败', envelope.requestId);
    }
    return response.data as unknown as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    const axiosErr = err as AxiosError<ApiEnvelope<unknown>>;
    const status = axiosErr.response?.status;
    const data = axiosErr.response?.data;
    if (status === 401 || status === 403) {
      clearStoredToken();
      onUnauthorized?.();
    }
    if (data && typeof data === 'object' && 'code' in data && 'message' in data) {
      throw new ApiError(
        (data as ApiEnvelope<unknown>).code,
        (data as ApiEnvelope<unknown>).message,
        (data as ApiEnvelope<unknown>).requestId,
      );
    }
    throw new ApiError(status ?? -1, axiosErr.message || '网络异常，请稍后重试');
  }
}

export const http = {
  get: <T>(url: string, params?: Record<string, unknown>) =>
    request<T>({ url, method: 'GET', params }),
  post: <T>(url: string, data?: unknown) => request<T>({ url, method: 'POST', data }),
  put: <T>(url: string, data?: unknown) => request<T>({ url, method: 'PUT', data }),
  patch: <T>(url: string, data?: unknown) => request<T>({ url, method: 'PATCH', data }),
  delete: <T>(url: string) => request<T>({ url, method: 'DELETE' }),
};
