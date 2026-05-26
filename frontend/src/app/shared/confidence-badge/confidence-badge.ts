import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-confidence-badge',
  imports: [CommonModule],
  template: `
    <span class="confidence" [class]="'confidence-' + confidence().toLowerCase()">
      <span class="dot" aria-hidden="true"></span>
      {{ confidence() }} confidence
    </span>
  `,
  styles: [`
    .confidence {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 2px 10px;
      border-radius: var(--radius-pill);
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text-muted);
    }
    .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: currentColor;
    }
    .confidence-high   { color: var(--success); border-color: var(--success-border); background: var(--success-soft); }
    .confidence-medium { color: var(--warning); border-color: var(--warning-border); background: var(--warning-soft); }
    .confidence-low    { color: var(--error);   border-color: var(--error-border);   background: var(--error-soft); }
  `]
})
export class ConfidenceBadge {
  confidence = input.required<string>();
}
