/** "yyyy-MM-dd HH:mm:ss" → "MM/dd HH:mm" */
export function shortDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  const [date = '', time = ''] = value.split(' ');
  const [, month = '', day = ''] = date.split('-');
  const hhmm = time.slice(0, 5);
  return `${month}/${day} ${hhmm}`;
}

/** "yyyy-MM-dd HH:mm:ss" → "HH:mm" */
export function timeShort(value: string | null | undefined): string {
  if (!value) return '—';
  const [, time = value] = value.split(' ');
  return time.slice(0, 5);
}

export function formatPercent(value: number): string {
  if (Number.isNaN(value)) return '—';
  return `${value.toFixed(value % 1 === 0 ? 0 : 1)}%`;
}

export function scoreTone(score: number): 'danger' | 'warning' | 'success' {
  if (score >= 90) return 'success';
  if (score >= 70) return 'warning';
  return 'danger';
}

export function relativeTime(value: string | null | undefined): string {
  if (!value) return '—';
  const target = new Date(value.replace(' ', 'T'));
  const diff = Date.now() - target.getTime();
  if (Number.isNaN(diff)) return value;
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return '刚刚';
  if (sec < 3600) return `${Math.floor(sec / 60)} 分钟前`;
  if (sec < 86400) return `${Math.floor(sec / 3600)} 小时前`;
  if (sec < 604800) return `${Math.floor(sec / 86400)} 天前`;
  return shortDateTime(value);
}

/** 将 Date 对象格式化为后端要求的 yyyy-MM-dd HH:mm:ss */
export function toBackendDateTime(date: Date | string | null): string {
  if (!date) return '';
  const d = date instanceof Date ? date : new Date(date);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

export function getInitial(name: string | null | undefined, fallback = '同'): string {
  if (!name) return fallback;
  return name.trim().slice(0, 1) || fallback;
}
