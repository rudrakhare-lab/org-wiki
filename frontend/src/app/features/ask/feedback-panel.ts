import { Component, input, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';

const LABELS = [
  'correct', 'partially_correct', 'wrong', 'incomplete', 'outdated',
  'conflicting_evidence', 'wrong_config', 'wrong_scope', 'missing_jira',
  'missing_pms_runtime', 'missing_runtime_context', 'unclear',
];

@Component({
  selector: 'app-feedback-panel',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="feedback">
      <div class="feedback-header">
        <span class="title">Helpful?</span>
        @if (submitted()) {
          <span class="submitted">Recorded</span>
        }
      </div>

      @if (!submitted()) {
        <div class="score-row" role="radiogroup" aria-label="Rate the answer">
          @for (s of scores; track s) {
            <button
              class="score-btn"
              [class.selected]="score() === s"
              (click)="score.set(s)"
              role="radio"
              [attr.aria-checked]="score() === s"
              [attr.aria-label]="s + ' out of 5'"
              type="button"
            >{{ s }}</button>
          }
          <span class="score-label">{{ scoreLabel() }}</span>
        </div>

        @if (score() > 0) {
          <div class="detail-row">
            <select [(ngModel)]="label" class="label-select" aria-label="Feedback label">
              <option value="">Choose a type…</option>
              @for (l of labels; track l) {
                <option [value]="l">{{ l.replace(/_/g, ' ') }}</option>
              }
            </select>

            @if (score() <= 3) {
              <textarea
                [(ngModel)]="correction"
                placeholder="What was wrong, or what should the answer have said?"
                class="correction-textarea"
                rows="2"
                aria-label="Correction details"
              ></textarea>
            }

            <button
              class="submit-btn"
              (click)="submit()"
              [disabled]="!label || submitting()"
              type="button"
            >
              {{ submitting() ? 'Submitting…' : 'Submit' }}
            </button>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .feedback {
      border-top: 1px solid var(--border);
      padding-top: 14px;
      margin-top: 4px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .feedback-header {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .title {
      font-size: 0.78rem;
      color: var(--text-muted);
      font-weight: 500;
    }
    .submitted {
      background: var(--success-soft);
      color: var(--success);
      padding: 2px 10px;
      border-radius: var(--radius-pill);
      font-size: 0.72rem;
      font-weight: 600;
      border: 1px solid var(--success-border);
    }

    .score-row {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .score-btn {
      width: 30px;
      height: 30px;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      background: var(--surface);
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--text-muted);
      transition: all 0.15s;

      &:hover {
        border-color: var(--border-strong);
        color: var(--text);
      }
      &.selected {
        background: var(--accent);
        color: var(--text-on-accent);
        border-color: var(--accent);
      }
      &:focus-visible {
        outline: 2px solid var(--accent-ring);
        outline-offset: 2px;
      }
    }
    .score-label {
      font-size: 0.78rem;
      color: var(--text-subtle);
      margin-left: 6px;
    }

    .detail-row {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .label-select {
      max-width: 280px;
      font-size: 0.85rem;
    }

    .correction-textarea {
      width: 100%;
      font-size: 0.85rem;
      resize: vertical;
      font-family: inherit;
      line-height: 1.5;
    }

    .submit-btn {
      align-self: flex-start;
      background: var(--accent);
      color: var(--text-on-accent);
      border: none;
      border-radius: var(--radius-sm);
      padding: 7px 16px;
      font-size: 0.82rem;
      font-weight: 500;
      transition: background 0.15s;

      &:hover:not(:disabled) { background: var(--accent-hover); }
      &:disabled {
        background: var(--surface-muted);
        color: var(--text-subtle);
        cursor: not-allowed;
      }
    }
  `]
})
export class FeedbackPanel {
  answerId = input.required<string>();
  question = input.required<string>();
  sources = input<string[]>([]);

  private api = inject(ApiService);

  scores = [1, 2, 3, 4, 5];
  labels = LABELS;

  score = signal(0);
  label = '';
  correction = '';
  submitting = signal(false);
  submitted = signal(false);

  scoreLabel() {
    const labels = ['', 'Wrong', 'Poor', 'Partial', 'Good', 'Excellent'];
    return labels[this.score()] ?? '';
  }

  submit() {
    if (!this.label) return;
    this.submitting.set(true);
    this.api.submitFeedback({
      answer_id: this.answerId(),
      question: this.question(),
      score: this.score(),
      label: this.label,
      correction: this.correction,
      sources: this.sources(),
    }).subscribe({
      next: () => {
        this.submitting.set(false);
        this.submitted.set(true);
      },
      error: () => {
        this.submitting.set(false);
      },
    });
  }
}
