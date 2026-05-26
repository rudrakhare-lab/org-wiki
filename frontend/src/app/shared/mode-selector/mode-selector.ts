/**
 * Two-option mode selector.
 *
 *   Deep Search   → mode='api'    — Anthropic API key, 9 backend tools, shows trace.
 *   Claude Code   → mode='agent'  — Server's Claude Code session (admin), live agent stream.
 *
 * The legacy 'claude-code' single-shot mode still exists in the backend for
 * backwards compatibility but is intentionally not exposed in the UI.
 */
import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { QueryMode } from '../../core/api.service';

export type { QueryMode };

@Component({
  selector: 'app-mode-selector',
  imports: [CommonModule],
  template: `
    <div class="mode-toggle" role="radiogroup" aria-label="Answer mode">
      <button
        class="mode-btn"
        [class.active]="currentMode() === 'api'"
        (click)="selectMode('api')"
        role="radio"
        [attr.aria-checked]="currentMode() === 'api'"
        title="Anthropic API · 9 backend tools · shows evidence trail"
      >
        Deep Search
        <span class="mode-sub">your API key</span>
      </button>
      <button
        class="mode-btn"
        [class.active]="currentMode() === 'agent'"
        [disabled]="!claudeCodeAvailable()"
        (click)="selectMode('agent')"
        role="radio"
        [attr.aria-checked]="currentMode() === 'agent'"
        [title]="claudeCodeAvailable()
          ? 'Runs the Claude Code CLI on the BACKEND machine (Read, Write, Bash, Grep, MCP). Not your browser.'
          : 'Claude Code CLI not installed on the backend machine'"
      >
        Claude Code
        <span class="mode-sub">
          @if (!claudeCodeAvailable()) { unavailable }
          @else if (localDev()) { local · headless }
          @else { backend session · live }
        </span>
      </button>
    </div>
  `,
  styles: [`
    .mode-toggle {
      display: inline-flex;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-pill);
      padding: 2px;
      gap: 2px;
    }

    .mode-btn {
      display: inline-flex;
      flex-direction: column;
      align-items: flex-start;
      padding: 5px 14px;
      border: none;
      border-radius: var(--radius-pill);
      font-size: 0.82rem;
      font-weight: 500;
      cursor: pointer;
      background: transparent;
      color: var(--text-muted);
      transition: background 0.15s, color 0.15s;
      white-space: nowrap;
      line-height: 1.2;

      &:hover:not(:disabled):not(.active) {
        background: var(--surface-muted);
        color: var(--text);
      }

      &.active {
        background: var(--accent);
        color: var(--text-on-accent);
        .mode-sub { color: rgba(255, 255, 255, 0.7); }
      }

      &:disabled {
        opacity: 0.45;
        cursor: not-allowed;
      }

      &:focus-visible {
        outline: 2px solid var(--accent-ring);
        outline-offset: 2px;
      }
    }

    .mode-sub {
      font-size: 0.65rem;
      font-weight: 400;
      color: var(--text-subtle);
      margin-top: 1px;
      letter-spacing: 0;
    }
  `]
})
export class ModeSelector {
  currentMode = input<QueryMode>('api');
  claudeCodeAvailable = input<boolean>(false);
  localDev = input<boolean>(false);

  modeChanged = output<QueryMode>();

  selectMode(mode: QueryMode) {
    if (mode === 'agent' && !this.claudeCodeAvailable()) return;
    if (mode === 'claude-code') return; // hidden mode — never emitted from the picker
    this.modeChanged.emit(mode);
  }
}
