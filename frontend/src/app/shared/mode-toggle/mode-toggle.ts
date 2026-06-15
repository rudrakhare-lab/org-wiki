import { Component, computed, inject } from '@angular/core';
import { AgentService } from '../../core/agent.service';

/**
 * Futuristic mode toggle. Floating pill (Conwo) / inline top strip (Infosec).
 * Label reflects the DESTINATION. Switching persists + reloads via AgentService.
 */
@Component({
  selector: 'app-mode-toggle',
  standalone: true,
  template: `
    <div class="mode-toggle" [class.strip]="isInfosec()" [class.floating]="!isInfosec()">
      <button type="button" class="mode-pill" (click)="switch()" [title]="label()">
        <span class="mode-pill-arrows" aria-hidden="true">⇄</span>
        <span class="mode-pill-label">{{ label() }}</span>
      </button>
    </div>
  `,
  styles: [`
    .mode-toggle.floating {
      position: fixed; top: 14px; right: 18px; z-index: 50;
    }
    .mode-toggle.strip {
      position: sticky; top: 0; z-index: 40;
      display: flex; justify-content: flex-end; align-items: center;
      padding: 8px 16px;
      border-bottom: 1px solid var(--border);
      background: color-mix(in srgb, var(--bg) 82%, transparent);
      backdrop-filter: saturate(140%) blur(8px);
    }
    .mode-pill {
      display: inline-flex; align-items: center; gap: 8px;
      font-family: var(--font-mono); font-size: 0.78rem; font-weight: 600;
      color: var(--text-on-accent); background: var(--accent);
      border: 1px solid var(--accent); border-radius: var(--radius-pill);
      padding: 7px 14px; cursor: pointer;
      box-shadow: 0 0 0 0 var(--accent-ring);
      transition: box-shadow .25s ease, transform .15s ease, background .2s ease;
    }
    .mode-pill:hover { background: var(--accent-hover); box-shadow: 0 0 18px var(--accent-ring); }
    .mode-pill:active { transform: scale(0.96); }
    .mode-pill-arrows { transition: transform .3s ease; }
    .mode-pill:hover .mode-pill-arrows { transform: rotate(180deg); }
  `]
})
export class ModeToggle {
  private agentSvc = inject(AgentService);

  isInfosec = computed(() => this.agentSvc.activeId() === 'infosec');
  target = computed(() => (this.agentSvc.activeId() === 'infosec' ? 'conwo' : 'infosec'));
  label = computed(() => {
    const id = this.target();
    const name = this.agentSvc.agents().find(a => a.id === id)?.display_name
      ?? (id === 'infosec' ? 'Infosec' : 'Conwo');
    return `Switch to ${name}`;
  });

  switch(): void {
    this.agentSvc.setActive(this.target());
  }
}
