import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

const ADMIN_TOKEN_KEY = 'conwo_admin_token';

// Functional CanActivate guard. Applied to every authenticated route in
// app.routes.ts so adding a new route doesn't require remembering to gate it
// in the component itself. If the user has no token, they're redirected to
// /login; the unauthorized URL is NOT preserved as a returnTo (out of scope
// for pilot — simpler is better).
export const authGuard: CanActivateFn = () => {
  const router = inject(Router);
  const token = (typeof localStorage !== 'undefined')
    ? (localStorage.getItem(ADMIN_TOKEN_KEY) ?? '')
    : '';
  if (token) return true;
  return router.parseUrl('/login');
};
