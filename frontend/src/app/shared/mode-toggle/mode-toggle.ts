import { Component, ElementRef, HostListener, inject, signal } from '@angular/core';
import { AgentService } from '../../core/agent.service';

/**
 * Agent switcher — a fixed dropdown anchored top-right in every mode.
 * Lists ALL agents from AgentService.agents(), highlights the active one, and
 * switches on click (persist + reload via AgentService.setActive). The trigger
 * glow accent is driven by --mt-* custom props, themed via :host-context so the
 * glow tracks the active agent's accent in dark mode.
 */
@Component({
  selector: 'app-mode-toggle',
  standalone: true,
  template: `
    <div class="agent-switcher" [class.open]="open()">
      <button class="trigger" (click)="open.set(!open())" [attr.aria-expanded]="open()" title="Switch agent">
        <span class="dot" [style.background]="activeAccent()"></span>
        <span class="name">{{ activeName() }}</span>
        <span class="caret">▾</span>
      </button>
      @if (open()) {
        <div class="menu" role="listbox">
          @for (a of agents(); track a.id) {
            <button class="item" role="option"
                    [class.active]="a.id === activeId()"
                    [class.locked]="!agentSvc.canUse(a.id)"
                    (click)="choose(a.id)">
              <span class="dot" [style.background]="a.accent || '#1e293b'"></span>
              <span class="name">{{ a.display_name }}</span>
              @if (a.id === activeId()) { <span class="check">✓</span> }
              @else if (agentSvc.accessFor(a.id) === 'pending') {
                <span class="badge">pending</span>
              }
              @else if (!agentSvc.canUse(a.id)) {
                <span class="lock" title="No access">🔒</span>
                <button class="req-btn" (click)="requestAccess(a.id, $event)">Request access</button>
              }
            </button>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    :host {
      /* Conwo (default): electric blue */
      --mt-color: #3b82f6;
      --mt-fill: #2563eb;
      --mt-glow: rgba(59, 130, 246, 0.55);
    }
    :host-context(body.theme-dark) {
      /* Dark agents: glow in the active accent */
      --mt-color: var(--accent);
      --mt-fill: color-mix(in srgb, var(--accent) 80%, black);
      --mt-glow: color-mix(in srgb, var(--accent) 60%, transparent);
    }

    .agent-switcher { position: fixed; top: 14px; right: 18px; z-index: 60; }
    .trigger { display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px;
      border-radius: 999px; border: 1px solid var(--border); background: var(--surface);
      color: var(--text); cursor: pointer; font: inherit; box-shadow: 0 0 0 0 var(--mt-glow);
      transition: box-shadow .2s ease, border-color .2s ease; }
    .trigger:hover { border-color: var(--mt-color); box-shadow: 0 0 0 4px var(--mt-glow); }
    .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex: none; }
    .caret { opacity: .6; }
    .menu { position: absolute; top: 110%; right: 0; min-width: 200px; padding: 6px;
      background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
      box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 2px; }
    .item { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border: 0;
      background: transparent; color: var(--text); border-radius: 8px; cursor: pointer;
      font: inherit; text-align: left; width: 100%; }
    .item:hover { background: var(--surface-hover); }
    .item.active { background: var(--accent-soft); }
    .item .check { margin-left: auto; color: var(--accent); }
    .item .name, .trigger .name { white-space: nowrap; }
    .item.locked { opacity: .7; }
    .item .lock { margin-left: auto; font-size: 13px; }
    .item .badge { margin-left: auto; font-size: 11px; padding: 1px 6px; border-radius: 999px;
      background: var(--accent-soft); color: var(--accent); font-weight: 600; }
    .req-btn { margin-left: 6px; padding: 2px 8px; border-radius: 6px; border: 1px solid var(--border);
      background: var(--surface); color: var(--text); font-size: 11px; cursor: pointer; font: inherit; }
    .req-btn:hover { border-color: var(--mt-color); }
  `]
})
export class ModeToggle {
  protected agentSvc = inject(AgentService);
  protected open = signal(false);
  private host = inject(ElementRef<HTMLElement>);

  @HostListener('document:click', ['$event'])
  onDocClick(ev: MouseEvent): void {
    if (this.open() && !this.host.nativeElement.contains(ev.target as Node)) {
      this.open.set(false);
    }
  }

  protected agents = this.agentSvc.agents;       // signal<Agent[]>
  protected activeId = this.agentSvc.activeId;    // signal<string>
  protected activeName(): string { return this.agentSvc.activeName(); }
  protected activeAccent(): string { return this.agentSvc.active()?.accent || '#1e293b'; }

  protected choose(id: string): void {
    if (!this.agentSvc.canUse(id)) return;   // locked — ignore
    this.open.set(false);
    this.agentSvc.setActive(id);
  }

  protected requestAccess(id: string, ev: Event): void {
    ev.stopPropagation();                     // don't trigger choose()
    this.agentSvc.requestAccess(id);
  }
}
