import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IngestPlan, IngestOperation } from '../../core/api.service';

@Component({
  selector: 'app-plan-step',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="plan-step">
      <div class="plan-header">
        <h2>Review Ingestion Plan</h2>
        <span class="filename">{{ filename() }}</span>
      </div>

      <div class="summary-box">
        <div class="section-label">Document Summary</div>
        <ul>
          @for (bullet of plan().summary_bullets; track bullet) {
            <li>{{ bullet }}</li>
          }
        </ul>
      </div>

      <div class="classification-badges">
        <div class="badge">
          <span class="badge-label">Type</span>
          <span class="badge-value">{{ plan().classification }}</span>
        </div>
        <div class="badge">
          <span class="badge-label">Target module</span>
          <span class="badge-value">{{ plan().target_slug }}</span>
        </div>
        <div class="badge">
          <span class="badge-label">Action</span>
          <span class="badge-value">{{ hasExistingModule() ? 'Update existing page' : 'Create new page' }}</span>
        </div>
      </div>

      <div class="ops-grid">
        <div class="ops-col">
          <div class="section-label">Files to create ({{ creates().length }})</div>
          <ul class="ops-list">
            @for (op of creates(); track op.path) {
              <li>
                <span class="op-icon">📄</span>
                <span class="op-path">{{ op.path }}</span>
                @if (op.preview) {
                  <span class="op-preview">{{ op.preview }}</span>
                }
              </li>
            }
            @if (creates().length === 0) {
              <li class="empty">None</li>
            }
          </ul>
        </div>

        <div class="ops-col">
          <div class="section-label">Files to modify ({{ edits().length }})</div>
          <ul class="ops-list">
            @for (op of edits(); track op.path) {
              <li>
                <span class="op-icon">✏️</span>
                <span class="op-path">{{ op.path }}</span>
                <span class="op-desc">{{ op.change_description }}</span>
              </li>
            }
            @if (edits().length === 0) {
              <li class="empty">None</li>
            }
          </ul>
        </div>
      </div>

      @if (plan().cross_references.length) {
        <div class="cross-refs">
          <div class="section-label">Cross-references to create ({{ plan().cross_references.length }})</div>
          <ul class="ops-list">
            @for (ref of plan().cross_references; track ref) {
              <li><span class="op-icon">🔗</span><span class="op-path">{{ ref }}</span></li>
            }
          </ul>
        </div>
      }

      @if (plan().warnings.length) {
        <div class="warnings-box">
          @for (w of plan().warnings; track w) {
            <div class="warning-item">⚠ {{ w }}</div>
          }
        </div>
      }

      <div class="plan-actions">
        <button class="btn-secondary" (click)="cancel.emit()">Cancel</button>
        <button class="btn-approve" (click)="approve.emit()">Approve & Execute →</button>
      </div>
    </div>
  `,
})
export class PlanStep {
  plan = input.required<IngestPlan>();
  filename = input<string>('');
  sessionId = input<string>('');

  approve = output<void>();
  cancel = output<void>();

  creates(): IngestOperation[] {
    return this.plan().operations.filter(o => o.type === 'create');
  }

  edits(): IngestOperation[] {
    return this.plan().operations.filter(o => o.type !== 'create');
  }

  hasExistingModule(): boolean {
    return this.plan().operations.some(
      o => o.type !== 'create' && o.path.startsWith('wiki/modules/')
    );
  }
}
