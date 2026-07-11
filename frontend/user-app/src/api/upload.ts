import type { FileUploadResponse, UploadBizType } from '@xunji/shared';

import { http } from './http';

/**
 * 上传文件到后端 /files/upload，必须带 bizType。
 * 见 backend/app/item/router.py:upload_file
 */
export function uploadFile(file: File, bizType: UploadBizType) {
  const form = new FormData();
  form.append('file', file);
  form.append('bizType', bizType);
  return http.upload<FileUploadResponse>('/files/upload', form);
}
