import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { ApiService } from './api.service';

const ADMIN_TOKEN_KEY = 'conwo_admin_token';

/**
 * Role guard factory — allow only the listed roles, else redirect to /ask
 * (a route every approved user can reach). Apply AFTER authGuard, which already
 * enforces token + approval; this layer only enforces role.
 *
 *   roleGuard(['admin'])               → admin-only (dashboard, traces, admin)
 *   roleGuard(['admin', 'developer'])  → ingest, graph
 *
 * Returns a UrlTree (not false) so a denied route redirects rather than dead-ends,
 * matching authGuard.
 */
export function roleGuard(allowed: string[]): CanActivateFn {
  return () => {
    const router = inject(Router);
    const api = inject(ApiService);
    if (allowed.includes(api.getUserRole())) return true;
    return router.parseUrl('/ask');
  };
}

/** Guard for the /pending screen itself: bounce already-approved users to /ask,
 *  and users with no token to /login. */
export const pendingGuard: CanActivateFn = () => {
  const router = inject(Router);
  const api = inject(ApiService);
  const token = (typeof localStorage !== 'undefined')
    ? (localStorage.getItem(ADMIN_TOKEN_KEY) ?? '')
    : '';
  if (!token) return router.parseUrl('/login');
  if (api.isApproved()) return router.parseUrl('/ask');
  return true;
};
