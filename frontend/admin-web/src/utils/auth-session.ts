export interface AdminSessionProfile {
  role: string;
}

export function hasAdminRouteAccess(
  token: string | null,
  profile: AdminSessionProfile | null,
  initialized: boolean,
): boolean {
  return initialized && Boolean(token) && profile?.role === 'ADMIN';
}
