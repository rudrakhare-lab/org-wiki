import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  ApiService,
  WikiProposal,
  ProposalApplyResult,
  ProposalStatus,
  ProposalType,
} from '../../core/api.service';

const TYPE_LABEL: Record<ProposalType, string> = {
  new: 'NEW',
  edit: 'EDIT',
  append: 'APPEND',
  multi_edit: 'MULTI',
  legacy_text: 'LEGACY',
};

@Component({
  selector: 'app-wiki-proposals-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <section class="admin-section">
      <div class="section-header">
        <h2>Wiki Proposal Queue</h2>
        <div class="header-controls">
          <label>
            Status:
            <select [(ngModel)]="filterStatus" (change)="load()" class="status-filter">
              <option value="pending">pending</option>
              <option value="applied">applied</option>
              <option value="rejected">rejected</option>
              <option value="">all</option>
            </select>
          </label>
          <button class="refresh-btn" (click)="load()">↻ Refresh</button>
        </div>
      </div>

      @if (loading()) {
        <p class="loading-text">Loading…</p>
      } @else if (proposals().length === 0) {
        <div class="empty-state">No proposals match this filter.</div>
      } @else {
        <table class="admin-table proposals-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Path / scope</th>
              <th>Submitter</th>
              <th>Created</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            @for (p of proposals(); track p.id) {
              <tr [class.row-selected]="selected()?.id === p.id" (click)="select(p)">
                <td>
                  <span class="type-badge" [class]="'type-' + p.proposal_type">
                    {{ typeLabelFor(p.proposal_type) }}
                  </span>
                </td>
                <td class="path-cell">
                  @if (p.proposal_type === 'multi_edit') {
                    {{ p.edits?.length ?? 0 }} file{{ (p.edits?.length ?? 0) === 1 ? '' : 's' }}
                  } @else {
                    <code>{{ p.page_path || '—' }}</code>
                  }
                </td>
                <td>{{ p.submitter_email }}</td>
                <td>{{ p.created_at | date:'short' }}</td>
                <td><span class="status-pill" [class]="'status-' + p.status">{{ p.status }}</span></td>
                <td>
                  <button type="button" class="link-btn" (click)="select(p); $event.stopPropagation()">View</button>
                </td>
              </tr>
            }
          </tbody>
        </table>
      }

      @if (selected(); as p) {
        <div class="proposal-detail">
          <div class="detail-header">
            <h3>
              <span class="type-badge" [class]="'type-' + p.proposal_type">
                {{ typeLabelFor(p.proposal_type) }}
              </span>
              {{ p.proposal_type === 'multi_edit' ? 'Atomic multi-file edit' : (p.page_path || '(no path)') }}
            </h3>
            <button type="button" class="close-btn" (click)="select(null)">✕</button>
          </div>

          <dl class="detail-meta">
            <dt>ID</dt><dd><code>{{ p.id }}</code></dd>
            <dt>Submitter</dt><dd>{{ p.submitter_email }}</dd>
            <dt>Created</dt><dd>{{ p.created_at | date:'medium' }}</dd>
            <dt>Status</dt><dd><span class="status-pill" [class]="'status-' + p.status">{{ p.status }}</span></dd>
            @if (p.reason) { <dt>Reason</dt><dd>{{ p.reason }}</dd> }
            @if (p.answer_id) { <dt>Answer ID</dt><dd><code>{{ p.answer_id }}</code></dd> }
            @if (p.applied_at) { <dt>Applied</dt><dd>{{ p.applied_at | date:'medium' }} by {{ p.applied_by }}</dd> }
            @if (p.admin_note) { <dt>Admin note</dt><dd>{{ p.admin_note }}</dd> }
          </dl>

          @if (p.proposal_type === 'legacy_text') {
            <div class="legacy-banner">
              ⚠️ <strong>Legacy proposal.</strong> Edit the wiki manually first, then click
              <em>Mark Applied</em> to record it in the audit trail.
            </div>
          }

          <!-- Type-specific body -->
          @switch (p.proposal_type) {
            @case ('new') {
              <div class="detail-section">
                <h4>Proposed new page content</h4>
                <pre class="content-block">{{ p.content }}</pre>
              </div>
            }
            @case ('edit') {
              <div class="detail-section">
                <h4>Old (existing in <code>{{ p.page_path }}</code>)</h4>
                <pre class="content-block old-content">{{ p.old_string }}</pre>
              </div>
              <div class="detail-section">
                <h4>New (proposed replacement)</h4>
                <pre class="content-block new-content">{{ p.new_string }}</pre>
              </div>
            }
            @case ('append') {
              <div class="detail-section">
                <h4>Content to append to <code>{{ p.page_path }}</code></h4>
                <pre class="content-block">{{ p.content }}</pre>
              </div>
            }
            @case ('multi_edit') {
              @for (e of p.edits ?? []; track $index; let i = $index) {
                <div class="detail-section">
                  <h4>Edit {{ i + 1 }} — <code>{{ e.page_path }}</code></h4>
                  <div class="multi-edit-pair">
                    <div>
                      <div class="pair-label">old</div>
                      <pre class="content-block old-content">{{ e.old_string }}</pre>
                    </div>
                    <div>
                      <div class="pair-label">new</div>
                      <pre class="content-block new-content">{{ e.new_string }}</pre>
                    </div>
                  </div>
                </div>
              }
            }
            @case ('legacy_text') {
              <div class="detail-section">
                <h4>Free-text proposed change</h4>
                <pre class="content-block">{{ p.proposed_change || '(no body)' }}</pre>
              </div>
            }
          }

          @if (p.suggested_companion_edit; as companion) {
            <div class="companion-callout">
              <strong>AI also suggested:</strong> {{ companion.note }}
              @if (companion.edits && companion.edits.length > 0) {
                <ul>
                  @for (ce of companion.edits; track ce.page_path) {
                    <li>
                      <code>{{ ce.page_path }}</code>
                      — {{ ce.reciprocal_field }}:
                      @if (ce.add) { add <code>{{ ce.add }}</code> }
                      @if (ce.remove) { remove <code>{{ ce.remove }}</code> }
                    </li>
                  }
                </ul>
              }
              <small class="companion-hint">Not auto-created — propose separately if desired.</small>
            </div>
          }

          @if (p.validation_log && p.validation_log.length > 0) {
            <details class="validation-log">
              <summary>Pre-apply checks ({{ p.validation_log.length }})</summary>
              <ul>
                @for (line of p.validation_log; track $index) { <li>{{ line }}</li> }
              </ul>
            </details>
          }

          @if (p.status === 'pending') {
            <div class="detail-actions">
              @if (p.proposal_type === 'legacy_text') {
                <button type="button" class="apply-btn"
                        [disabled]="busyId() === p.id"
                        (click)="markApplied(p)">
                  {{ busyId() === p.id ? 'Marking…' : 'Mark Applied' }}
                </button>
              } @else {
                <button type="button" class="apply-btn"
                        [disabled]="busyId() === p.id"
                        (click)="apply(p)">
                  {{ busyId() === p.id ? 'Applying…' : (p.proposal_type === 'multi_edit' ? 'Apply All' : 'Apply') }}
                </button>
              }
              <div class="reject-row">
                <input type="text" class="reject-note" placeholder="Reason (optional)"
                       [(ngModel)]="rejectNote" />
                <button type="button" class="reject-btn"
                        [disabled]="busyId() === p.id"
                        (click)="reject(p)">
                  {{ busyId() === p.id ? 'Rejecting…' : 'Reject' }}
                </button>
              </div>
            </div>
          }

          @if (actionResult(); as r) {
            <div class="action-result" [class.success]="r.success">
              {{ r.success ? '✓' : '✗' }}
              {{ formatResultMessage(r) }}
            </div>
          }
        </div>
      }
    </section>
  `,
  styleUrl: './wiki-proposals-panel.scss',
})
export class WikiProposalsPanel implements OnInit {
  private api = inject(ApiService);

  filterStatus: ProposalStatus | '' = 'pending';
  proposals = signal<WikiProposal[]>([]);
  loading = signal(false);
  selected = signal<WikiProposal | null>(null);
  busyId = signal<string | null>(null);
  actionResult = signal<ProposalApplyResult | null>(null);
  rejectNote = '';

  ngOnInit() { this.load(); }

  typeLabelFor(t: ProposalType): string { return TYPE_LABEL[t] || t.toUpperCase(); }

  load() {
    this.loading.set(true);
    this.actionResult.set(null);
    const obs = this.filterStatus
      ? this.api.listProposals(this.filterStatus as ProposalStatus)
      : this.api.listProposals();
    obs.subscribe({
      next: r => {
        this.proposals.set(r.proposals);
        this.loading.set(false);
        // Preserve selection across refresh if id still present
        const sel = this.selected();
        if (sel) {
          const refreshed = r.proposals.find(p => p.id === sel.id);
          this.selected.set(refreshed ?? null);
        }
      },
      error: () => { this.loading.set(false); this.proposals.set([]); },
    });
  }

  select(p: WikiProposal | null) {
    this.selected.set(p);
    this.actionResult.set(null);
    this.rejectNote = '';
  }

  apply(p: WikiProposal) {
    this.busyId.set(p.id);
    this.actionResult.set(null);
    this.api.applyProposal(p.id).subscribe({
      next: r => { this.busyId.set(null); this.actionResult.set(r); this.load(); },
      error: err => {
        this.busyId.set(null);
        this.actionResult.set(err?.error?.detail ?? { success: false, error: 'Apply failed' });
      },
    });
  }

  markApplied(p: WikiProposal) {
    this.busyId.set(p.id);
    this.actionResult.set(null);
    this.api.markProposalApplied(p.id).subscribe({
      next: r => { this.busyId.set(null); this.actionResult.set(r); this.load(); },
      error: err => {
        this.busyId.set(null);
        this.actionResult.set(err?.error?.detail ?? { success: false, error: 'Mark-applied failed' });
      },
    });
  }

  reject(p: WikiProposal) {
    this.busyId.set(p.id);
    this.actionResult.set(null);
    this.api.rejectProposal(p.id, this.rejectNote || undefined).subscribe({
      next: r => { this.busyId.set(null); this.actionResult.set(r); this.rejectNote = ''; this.load(); },
      error: err => {
        this.busyId.set(null);
        this.actionResult.set(err?.error?.detail ?? { success: false, error: 'Reject failed' });
      },
    });
  }

  formatResultMessage(r: ProposalApplyResult): string {
    if (r.success) {
      if (r.files_written && r.files_written.length > 0) {
        return `Applied — wrote ${r.files_written.length} file${r.files_written.length === 1 ? '' : 's'}: ${r.files_written.join(', ')}`;
      }
      return r.message || 'Done.';
    }
    const hint = this.hintForCode(r.code);
    return `${r.error || r.message || 'Failed'}${hint ? ` — ${hint}` : ''}`;
  }

  private hintForCode(code?: string): string {
    if (code === 'stale_proposal') return 'Page changed since this proposal was created. Reject and ask the user to re-propose.';
    if (code === 'write_io_error') return 'File system write failed. Check disk space and permissions.';
    if (code === 'legacy_text_refused') return 'Wrong endpoint — use Mark Applied for legacy proposals.';
    if (code === 'already_applied') return 'Already applied (idempotent).';
    return '';
  }
}
