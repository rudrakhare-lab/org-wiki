import { Component, computed, inject } from '@angular/core';
import { AgentService } from '../../core/agent.service';

/**
 * Futuristic mode toggle — a single fixed pill anchored top-right in BOTH modes.
 * Glassy, glowing, gently pulsing, with a hover "shine" sweep. Accent is driven
 * by --mt-* custom props: electric BLUE in Conwo, VIOLET in Infosec (themed via
 * :host-context). Label = destination. Switching persists + reloads via AgentService.
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
    :host {
      /* Conwo (default): electric blue */
      --mt-color: #3b82f6;
      --mt-fill: #2563eb;
      --mt-glow: rgba(59, 130, 246, 0.55);
    }
    :host-context(body.theme-infosec) {
      /* Infosec: violet, matching the dark theme */
      --mt-color: #a78bfa;
      --mt-fill: #8b5cf6;
      --mt-glow: rgba(167, 139, 250, 0.6);
    }

    .mode-toggle {
      position: fixed;
      top: 14px;
      right: 18px;
      z-index: 60;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      overflow: hidden;
      font-family: var(--font-mono);
      font-size: 0.76rem;
      font-weight: 600;
      letter-spacing: 0.03em;
      color: var(--mt-color);
      background: color-mix(in srgb, var(--surface) 70%, transparent);
      border: 1px solid var(--mt-color);
      border-radius: var(--radius-pill);
      padding: 8px 16px;
      cursor: pointer;
      backdrop-filter: saturate(150%) blur(10px);
      -webkit-backdrop-filter: saturate(150%) blur(10px);
      transition: color .25s ease, background .25s ease, box-shadow .3s ease,
                  transform .15s ease, border-color .25s ease;
      animation: mt-pulse 3s ease-in-out infinite;
    }

    /* hover "shine" sweep */
    .mode-toggle::before {
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(120deg, transparent 30%,
                  color-mix(in srgb, var(--mt-color) 38%, transparent) 50%, transparent 70%);
      transform: translateX(-130%);
      transition: transform .6s ease;
      pointer-events: none;
    }
    .mt-arrows, .mt-label { position: relative; z-index: 1; }
    .mt-arrows { transition: transform .45s ease; }

    .mode-toggle:hover {
      color: #fff;
      background: var(--mt-fill);
      border-color: var(--mt-fill);
      transform: translateY(-1px);
      box-shadow: 0 0 30px var(--mt-glow), 0 0 10px var(--mt-glow);
      animation: none;
    }
    .mode-toggle:hover::before { transform: translateX(130%); }
    .mode-toggle:hover .mt-arrows { transform: rotate(180deg); }
    .mode-toggle:active { transform: scale(0.97); }

    @keyframes mt-pulse {
      0%, 100% { box-shadow: 0 0 12px var(--mt-glow),
                             inset 0 0 8px color-mix(in srgb, var(--mt-color) 10%, transparent); }
      50%      { box-shadow: 0 0 22px var(--mt-glow),
                             inset 0 0 13px color-mix(in srgb, var(--mt-color) 22%, transparent); }
    }
    @media (prefers-reduced-motion: reduce) {
      .mode-toggle { animation: none; }
      .mode-toggle::before { display: none; }
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
