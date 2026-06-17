import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { AgentService, ACTIVE_BASE_KEY, ACTIVE_ACCENT_KEY } from './agent.service';
import { ApiService } from './api.service';

describe('AgentService theme hints', () => {
  function setup(agents: any[], activeId: string) {
    localStorage.setItem('conwo_active_agent', activeId);
    TestBed.configureTestingModule({
      providers: [
        AgentService,
        { provide: ApiService, useValue: { getAgents: () => of(agents) } },
      ],
    });
    return TestBed.inject(AgentService);
  }

  afterEach(() => localStorage.clear());

  it('persists dark base + accent for a created agent', () => {
    const svc = setup([], 'legal');
    svc.agents.set([{ id: 'legal', display_name: 'Legal', accent: '#3fa7d6', theme_base: 'dark', modes: ['api'], has_jira: false, has_pms: false, description: '' } as any]);
    svc.persistThemeHints();
    expect(localStorage.getItem(ACTIVE_BASE_KEY)).toBe('dark');
    expect(localStorage.getItem(ACTIVE_ACCENT_KEY)).toBe('#3fa7d6');
  });

  it('falls back to light base for conwo before list loads', () => {
    const svc = setup([], 'conwo');
    expect(svc.activeBase()).toBe('light');
  });
});
