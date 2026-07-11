export const MOBILE_NAV_ORDER = [
  'home',
  'search',
  'publish',
  'notifications',
  'profile',
] as const;

export type MobileNavKey = (typeof MOBILE_NAV_ORDER)[number];

export function isMobileNavActive(key: MobileNavKey, path: string): boolean {
  if (key === 'home') return path === '/';
  if (key === 'publish') return path.startsWith('/publish/');
  if (key === 'notifications') {
    return path === '/notifications' || path.startsWith('/announcements/');
  }
  return path.startsWith(`/${key}`);
}
