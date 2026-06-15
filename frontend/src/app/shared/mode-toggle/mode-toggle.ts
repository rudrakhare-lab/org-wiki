import { Component, computed, inject } from '@angular/core';
import { AgentService } from '../../core/agent.service';

/**
 * Futuristic mode toggle — a single fixed pill anchored top-right in BOTH modes.
 * Glassy, glowing, gently pulsing; themed entirely via CSS vars so it adapts:
 * violet glow in Infosec, on-brand slate glow in Conwo. Label = destination.
 * Switching persists + reloads via AgentService.
 */
@Component({
  selector: 'app-mode-toggle',
  standalone: true,
  template: `
    <button type="button" class="mode-toggle" (click)="switch()" [title]="label()">
      <span class="mt-arrows" aria-hidden="true">⇄</span>
      <span class="mt-label">{{ label() }}</span>
    </button>
  `,
  styles: [`
    .mode-toggle {
      position: fixed;
      top: 16px;
      right: 20px;
      z-index: 60;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-family: var(--font-mono);
      font-size: 0.76rem;
      font-weight: 600;
      letter-spacing: 0.02em;
      color: var(--accent);
      background: color-mix(in srgb, var(--surface) 68%, transparent);
      border: 1px solid var(--accent);
      border-radius: var(--radius-pill);
      padding: 8px 16px;
      cursor: pointer;
      backdrop-filter: saturate(140%) blur(10px);
      -webkit-backdrop-filter: saturate(140%) blur(10px);
      transition: box-shadow .3s ease, transform .15s ease, color .25s ease, background .25s ease;
      animation: mt-pulse 3.2s ease-in-out infinite;
    }
    .mode-toggle:hover {
      color: var(--text-on-accent);
      background: var(--accent);
      transform: translateY(-1px);
      box-shadow: 0 0 26px var(--accent-ring), 0 0 8px var(--accent-ring);
    }
    .mode-toggle:active { transform: scale(0.97); }
    .mt-arrows { transition: transform .4s ease; }
    .mode-toggle:hover .mt-arrows { transform: rotate(180deg); }

    @keyframes mt-pulse {
      0%, 100% { box-shadow: 0 0 12px var(--accent-ring),
                             inset 0 0 0 1px color-mix(in srgb, var(--accent) 16%, transparent); }
      50%      { box-shadow: 0 0 22px var(--accent-ring),
                             inset 0 0 0 1px color-mix(in srgb, var(--accent) 30%, transparent); }
    }
    @media (prefers-reduced-motion: reduce) {
      .mode-toggle { animation: none; }
    }
  `]
})
export class ModeToggle {
  private agentSvc = inject(AgentService);

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
