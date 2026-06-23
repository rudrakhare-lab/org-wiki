import { HttpInterceptorFn } from '@angular/common/http';

const ADMIN_TOKEN_KEY = 'conwo_admin_token';
const ACTIVE_AGENT_KEY = 'conwo_active_agent';

const PUBLIC_PATHS = ['/health', '/health/claude-code'];

function isPublicPath(url: string): boolean {
  return PUBLIC_PATHS.some(p => url.endsWith(p));
}

function readLocal(key: string): string {
  try {
    return (typeof localStorage !== 'undefined') ? (localStorage.getItem(key) ?? '') : '';
  } catch {
    return '';
  }
}

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  if (isPublicPath(req.url)) {
    return next(req);
  }

  // Always stamp the active agent (default conwo) so every API call is
  // agent-scoped. The backend defaults to conwo when the header is absent,
  // so this is additive and safe for existing endpoints.
  const agentId = readLocal(ACTIVE_AGENT_KEY) || 'conwo';
  const setHeaders: Record<string, string> = { 'X-Agent-Id': agentId };

  // Attach the bearer token unless the caller set Authorization explicitly.
  if (!req.headers.has('Authorization')) {
    const token = readLocal(ADMIN_TOKEN_KEY);
    if (token) {
      setHeaders['Authorization'] = `Bearer ${token}`;
    }
  }

  return next(req.clone({ setHeaders }));
};
