import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { ApiService } from './api.service';

const ADMIN_TOKEN_KEY = 'conwo_admin_token';

// Functional CanActivate guard. Applied to every authenticated route in
// app.routes.ts so adding a new route doesn't require remembering to gate it
// in the component itself.
//   - No token            → /login
//   - Token but unapproved → /pending (approval flow)
//   - Otherwise            → allow
// Approval is read optimistically from localStorage (the backend is the real
// gate); app bootstrap hydrates the real flag via /auth/me.
export const authGuard: CanActivateFn = () => {
  const router = inject(Router);
  const api = inject(ApiService);
  const token = (typeof localStorage !== 'undefined')
    ? (localStorage.getItem(ADMIN_TOKEN_KEY) ?? '')
    : '';
  if (!token) return router.parseUrl('/login');
  if (!api.isApproved()) return router.parseUrl('/pending');
  return true;
};
