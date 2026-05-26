import { HttpInterceptorFn } from '@angular/common/http';

const ADMIN_TOKEN_KEY = 'conwo_admin_token';

// Public endpoints that should NOT receive an Authorization header. Everything
// else — including /status, /conversations, /query, /admin/* — gets the
// stored bearer token attached automatically, so per-method header attachment
// becomes optional. Adding a new authenticated endpoint requires no special
// handling.
const PUBLIC_PATHS = ['/health', '/health/claude-code'];

function isPublicPath(url: string): boolean {
  return PUBLIC_PATHS.some(p => url.endsWith(p));
}

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  if (isPublicPath(req.url)) {
    return next(req);
  }
  // Do not override an Authorization header that was set explicitly by a
  // caller (preserves the existing manual-attachment patterns until they're
  // cleaned up in a later pass).
  if (req.headers.has('Authorization')) {
    return next(req);
  }
  const token = (typeof localStorage !== 'undefined')
    ? (localStorage.getItem(ADMIN_TOKEN_KEY) ?? '')
    : '';
  if (!token) {
    return next(req);
  }
  const authed = req.clone({
    setHeaders: { Authorization: `Bearer ${token}` },
  });
  return next(authed);
};
