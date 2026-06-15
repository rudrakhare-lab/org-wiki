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
export const DEFAULT_AGENT_ID = 'conwo';

@Injectable({ providedIn: 'root' })
export class AgentService {
  private api = inject(ApiService);

  readonly agents = signal<Agent[]>([]);
  readonly activeId = signal<string>(this.readPersisted());

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
      },
      error: () => { /* leave default; switcher just won't populate */ },
    });
  }

  /** The active agent's full record, if the list is loaded. */
  active(): Agent | undefined {
    return this.agents().find((a) => a.id === this.activeId());
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
    if (reload && typeof window !== 'undefined') {
      window.location.assign('/ask');
    }
  }
}
