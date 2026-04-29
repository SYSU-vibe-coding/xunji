/** 后端统一响应包：见 backend/app/common/response.py */
export interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
  requestId: string;
  timestamp: string;
}

export interface PageData<T> {
  list: T[];
  pageNo: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface PageQuery {
  pageNo?: number;
  pageSize?: number;
}
