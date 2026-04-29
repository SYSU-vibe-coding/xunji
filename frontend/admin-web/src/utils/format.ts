export function shortDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  const [date = '', time = ''] = value.split(' ');
  const [, month = '', day = ''] = date.split('-');
  return `${month}/${day} ${time.slice(0, 5)}`;
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

export function getInitial(name: string | null | undefined, fallback = '管'): string {
  if (!name) return fallback;
  return name.trim().slice(0, 1) || fallback;
}
