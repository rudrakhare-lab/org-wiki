import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, SyncStatus, IngestItem, FeedbackRecord } from '../../core/api.service';
import { WikiProposalsPanel } from './wiki-proposals-panel';

@Component({
  selector: 'app-admin-dashboard',
  imports: [CommonModule, FormsModule, WikiProposalsPanel],
  template: `
    <div class="admin-page">
      <header class="admin-header">
        <h1>⚙️ Admin Dashboard</h1>
        <p>Sync status, ingestion queue, and feedback review.</p>
      </header>

      <!-- Sync Status -->
        <section class="admin-section">
          <div class="section-header">
            <h2>Sync Status</h2>
            <button class="refresh-btn" (click)="loadStatus()">↻ Refresh</button>
          </div>

          @if (status()) {
            <div class="status-grid">
              <div class="status-card">
                <div class="status-label">Jira tickets</div>
                <div class="status-value">{{ status()!.jira.ticket_count | number }}</div>
                <div class="status-meta">{{ status()!.jira.last_sync_line || 'No sync log' }}</div>
                <button class="trigger-btn" (click)="triggerSync()" [disabled]="syncing()">
                  {{ syncing() ? 'Starting…' : '▶ Sync now' }}
                </button>
                @if (syncMessage()) {
                  <div class="sync-msg">{{ syncMessage() }}</div>
                }
              </div>
              <div class="status-card">
                <div class="status-label">Drive files</div>
                <div class="status-value">{{ status()!.drive.file_count }}</div>
                <div class="status-meta">{{ status()!.drive.last_sync || 'Never synced' }}</div>
              </div>
              <div class="status-card" [class.alert]="status()!.feedback.pending_count > 0">
                <div class="status-label">Pending feedback</div>
                <div class="status-value">{{ status()!.feedback.pending_count }}</div>
                <div class="status-meta">Needs admin review</div>
              </div>
            </div>
          } @else {
            <p class="loading-text">Loading status…</p>
          }
        </section>

        <!-- Ingest Queue -->
        <section class="admin-section">
          <div class="section-header">
            <h2>Ingest Queue</h2>
            <button class="refresh-btn" (click)="loadIngestQueue()">↻ Refresh</button>
          </div>
          @if (ingestQueue().length === 0) {
            <div class="empty-state">✓ No unprocessed files</div>
          } @else {
            <table class="admin-table">
              <thead><tr><th>Module</th><th>File</th><th>Action</th></tr></thead>
              <tbody>
                @for (item of ingestQueue(); track item.path) {
                  <tr>
                    <td><code>{{ item.module }}</code></td>
                    <td class="path-cell">{{ item.path }}</td>
                    <td>
                      <span class="manual-tag">Process via Claude Code</span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          }
        </section>

        <!-- Wiki Proposals (Track A) -->
        <app-wiki-proposals-panel />

        <!-- Feedback Review Queue -->
        <section class="admin-section">
          <div class="section-header">
            <h2>Feedback Review Queue</h2>
            <button class="refresh-btn" (click)="loadFeedback()">↻ Refresh</button>
          </div>
          @if (feedbackList().length === 0) {
            <div class="empty-state">✓ No pending feedback</div>
          } @else {
            @for (fb of feedbackList(); track fb.feedback_id) {
              <div class="feedback-card" [class.score-low]="fb.score <= 2" [class.score-mid]="fb.score === 3">
                <div class="fb-header">
                  <span class="score-pill" [class]="'score-' + fb.score">{{ fb.score }}/5</span>
                  <code class="label-tag">{{ fb.label }}</code>
                  <span class="fb-date">{{ fb.created_at | date:'short' }}</span>
                  <span class="fb-id">{{ fb.feedback_id }}</span>
                </div>
                <div class="fb-question">Q: {{ fb.question }}</div>
                @if (fb.correction) {
                  <div class="fb-correction">Correction: {{ fb.correction }}</div>
                }

                <div class="fb-actions">
                  <button class="preview-btn" (click)="previewPatch(fb)">Preview patch</button>
                  <button class="apply-btn" (click)="applyPatch(fb)" [disabled]="applying() === fb.feedback_id">
                    {{ applying() === fb.feedback_id ? 'Applying…' : 'Apply patch' }}
                  </button>
                </div>

                @if (patchPlan() && selectedFb()?.feedback_id === fb.feedback_id) {
                  <div class="patch-preview">
                    <div class="patch-header">Patch plan (dry-run)</div>
                    <pre>{{ patchPlan() }}</pre>
                  </div>
                }

                @if (applyResult() && selectedFb()?.feedback_id === fb.feedback_id) {
                  <div class="apply-result" [class.success]="applyResult()!.success">
                    {{ applyResult()!.success ? '✓ Patch applied' : '✗ Apply failed' }}
                    <pre>{{ applyResult()!.output }}</pre>
                  </div>
                }
              </div>
            }
          }
        </section>
    </div>
  `,
  styleUrl: './admin-dashboard.scss'
})
export class AdminDashboard implements OnInit {
  private api = inject(ApiService);

  status = signal<SyncStatus | null>(null);
  ingestQueue = signal<IngestItem[]>([]);
  feedbackList = signal<FeedbackRecord[]>([]);
  syncing = signal(false);
  syncMessage = signal('');
  applying = signal('');
  patchPlan = signal('');
  applyResult = signal<{ success: boolean; output: string } | null>(null);
  selectedFb = signal<FeedbackRecord | null>(null);

  ngOnInit() {
    // The route guard ensures the user is signed in. Admin endpoints will 403
    // for non-admin tokens — the panel surfaces that as a load error inline.
    this.loadAll();
  }

  loadAll() {
    this.loadStatus();
    this.loadIngestQueue();
    this.loadFeedback();
  }

  loadStatus() {
    this.api.getSyncStatus().subscribe({ next: s => this.status.set(s) });
  }

  loadIngestQueue() {
    this.api.getIngestQueue().subscribe({ next: q => this.ingestQueue.set(q) });
  }

  loadFeedback() {
    this.api.getFeedbackList('pending').subscribe({ next: f => this.feedbackList.set(f) });
  }

  triggerSync() {
    this.syncing.set(true);
    this.api.triggerSync().subscribe({
      next: r => {
        this.syncing.set(false);
        this.syncMessage.set(r.status === 'started' ? `Sync started (PID ${r.pid})` : r.status);
        setTimeout(() => this.syncMessage.set(''), 4000);
      },
      error: () => this.syncing.set(false),
    });
  }

  previewPatch(fb: FeedbackRecord) {
    this.selectedFb.set(fb);
    this.patchPlan.set('Loading…');
    this.applyResult.set(null);
    this.api.getPatchPlan(fb.feedback_id).subscribe({
      next: r => this.patchPlan.set(r.plan || '(no patch plan output)'),
      error: () => this.patchPlan.set('Error loading patch plan'),
    });
  }

  applyPatch(fb: FeedbackRecord) {
    this.selectedFb.set(fb);
    this.applying.set(fb.feedback_id);
    this.patchPlan.set('');
    this.api.applyPatch(fb.feedback_id).subscribe({
      next: r => {
        this.applying.set('');
        this.applyResult.set(r);
        if (r.success) this.loadFeedback();
      },
      error: err => {
        this.applying.set('');
        this.applyResult.set({ success: false, output: err?.error?.detail ?? 'Apply failed' });
      },
    });
  }
}
