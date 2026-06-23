/**
 * AgentService — the active AI agent (e.g. "conwo" or "infosec").
 *
 * Holds the active agent id as a signal, persisted to localStorage so the
 * authInterceptor can stamp every request with X-Agent-Id (it reads the same
 * key directly, avoiding a DI cycle). Loads the selectable agent list from the
 * backend's GET /agents. Switching agent persists the choice and reloads the
 * app so every surface re-initializes cleanly as the new agent.
 */
import { Injectable, inject, signal } from '@angular/core';
import { ApiService, Agent } from './api.service';

export const ACTIVE_AGENT_KEY = 'conwo_active_agent';
export const ACTIVE_BASE_KEY = 'conwo_active_base';     // 'light' | 'dark'
export const ACTIVE_ACCENT_KEY = 'conwo_active_accent'; // hex string
export const DEFAULT_AGENT_ID = 'conwo';

@Injectable({ providedIn: 'root' })
export class AgentService {
  private api = inject(ApiService);

  readonly agents = signal<Agent[]>([]);
  readonly activeId = signal<string>(this.readPersisted());
  readonly access = signal<Record<string, string>>({});

  private readPersisted(): string {
    try {
      return localStorage.getItem(ACTIVE_AGENT_KEY) || DEFAULT_AGENT_ID;
    } catch {
      return DEFAULT_AGENT_ID;
    }
  }

  /** Load the selectable agent list from the backend (best-effort). */
  loadAgents(): void {
    this.api.getAgents().subscribe({
      next: (list) => {
        this.agents.set(list);
        if (!list.some((a) => a.id === this.activeId())) {
          this.setActive(DEFAULT_AGENT_ID, false);
        }
        this.loadAccess();
      },
      error: () => { /* leave default; switcher just won't populate */ },
    });
  }

  loadAccess(): void {
    this.api.getMyAgentAccess().subscribe({
      next: (m) => this.access.set(m || {}),
      error: () => { /* leave empty; switcher treats unknown as locked */ },
    });
  }

  accessFor(id: string): string {
    return this.access()[id] ?? (id === DEFAULT_AGENT_ID ? 'open' : 'none');
  }

  canUse(id: string): boolean {
    const s = this.accessFor(id);
    return s === 'open' || s === 'granted';
  }

  requestAccess(id: string): void {
    this.access.update((m) => ({ ...m, [id]: 'pending' }));   // optimistic
    this.api.requestAgentAccess(id).subscribe({
      next: (r) => this.access.update((m) => ({ ...m, [id]: r.status })),
      error: () => this.access.update((m) => ({ ...m, [id]: 'none' })),  // revert
    });
  }

  /** The active agent's full record, if the list is loaded. */
  active(): Agent | undefined {
    return this.agents().find((a) => a.id === this.activeId());
  }

  /** Base theme of the active agent, with a safe fallback before the list loads. */
  activeBase(): 'light' | 'dark' {
    const a = this.active();
    if (a?.theme_base === 'light' || a?.theme_base === 'dark') return a.theme_base;
    return this.activeId() === DEFAULT_AGENT_ID ? 'light' : 'dark';
  }

  /** Persist base+accent so index.html can pre-apply them on next load (anti-flash). */
  persistThemeHints(): void {
    try {
      localStorage.setItem(ACTIVE_BASE_KEY, this.activeBase());
      const accent = this.active()?.accent;
      if (accent) localStorage.setItem(ACTIVE_ACCENT_KEY, accent);
      else localStorage.removeItem(ACTIVE_ACCENT_KEY);
    } catch { /* private mode */ }
  }

  activeName(): string {
    return this.active()?.display_name ?? 'Conwo';
  }

  /**
   * Switch the active agent. Persists + updates the signal. By default reloads
   * the app (navigates to /ask) so every surface re-inits as the new agent.
   */
  setActive(id: string, reload = true): void {
    if (id === this.activeId() && reload) return;
    try { localStorage.setItem(ACTIVE_AGENT_KEY, id); } catch { /* private mode */ }
    this.activeId.set(id);
    this.persistThemeHints(); // sync — the reload below would otherwise pre-empt the effect
    if (reload && typeof window !== 'undefined') {
      window.location.assign('/ask');
    }
  }
}
