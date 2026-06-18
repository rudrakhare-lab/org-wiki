import { Component, signal, computed, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, SyncStatus, SyncJob, IngestItem, FeedbackRecord, AdminUser } from '../../core/api.service';
import { WikiProposalsPanel } from './wiki-proposals-panel';

@Component({
  selector: 'app-admin-dashboard',
  imports: [CommonModule, FormsModule, WikiProposalsPanel],
  template: `
    <div class="admin-page">
      <header class="admin-header">
        <h1>⚙️ Admin Dashboard</h1>
        <p>User access, sync status, ingestion queue, and feedback review.</p>
      </header>

      <!-- Approvals (pending only) -->
      <section class="admin-section">
        <div class="section-header">
          <h2>Approvals</h2>
          <button class="refresh-btn" (click)="loadUsers()">↻ Refresh</button>
        </div>
        @if (usersError()) {
          <div class="empty-state">{{ usersError() }}</div>
        } @else if (pendingUsers().length === 0) {
          <div class="empty-state">✓ No pending approvals</div>
        } @else {
          <table class="admin-table">
            <thead>
              <tr><th>Email</th><th>Role to grant</th><th>Action</th></tr>
            </thead>
            <tbody>
              @for (u of pendingUsers(); track u.email) {
                <tr class="pending-row">
                  <td class="path-cell">{{ u.email }}</td>
                  <td>
                    <select class="role-select" [(ngModel)]="pendingRole[u.email]"
                            [disabled]="savingEmail() === u.email">
                      <option value="general">general</option>
                      <option value="developer">developer</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>
                  <td>
                    <button class="apply-btn" (click)="approve(u)" [disabled]="savingEmail() === u.email">
                      {{ savingEmail() === u.email ? 'Approving…' : 'Approve' }}
                    </button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        }
      </section>

      <!-- Users (approved only) -->
      <section class="admin-section">
        <div class="section-header">
          <h2>Users</h2>
          <button class="refresh-btn" (click)="loadUsers()">↻ Refresh</button>
        </div>
        @if (approvedUsers().length === 0) {
          <div class="empty-state">No approved users yet.</div>
        } @else {
          <table class="admin-table">
            <thead>
              <tr><th>Email</th><th>Role</th><th>Status</th></tr>
            </thead>
            <tbody>
              @for (u of approvedUsers(); track u.email) {
                <tr>
                  <td class="path-cell">{{ u.email }}</td>
                  <td>
                    <select class="role-select" [ngModel]="u.role"
                            (ngModelChange)="changeRole(u, $event)"
                            [disabled]="savingEmail() === u.email">
                      <option value="general">general</option>
                      <option value="developer">developer</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>
                  <td><span class="status-ok">✓ Approved</span></td>
                </tr>
              }
            </tbody>
          </table>
        }
      </section>

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
export class AdminDashboard implements OnInit, OnDestroy {
  private api = inject(ApiService);

  status = signal<SyncStatus | null>(null);
  ingestQueue = signal<IngestItem[]>([]);
  feedbackList = signal<FeedbackRecord[]>([]);
  users = signal<AdminUser[]>([]);
  pendingUsers = computed(() => this.users().filter(u => !u.approved));
  approvedUsers = computed(() => this.users().filter(u => u.approved));
  pendingRole: Record<string, string> = {};
  usersError = signal('');
  savingEmail = signal('');
  syncing = signal(false);
  syncMessage = signal('');
  private syncPoll: ReturnType<typeof setInterval> | null = null;
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
    this.loadUsers();
    this.loadStatus();
    this.loadIngestQueue();
    this.loadFeedback();
  }

  loadUsers() {
    this.usersError.set('');
    this.api.adminListUsers().subscribe({
      next: r => {
        this.users.set(r.users);
        for (const u of r.users) {
          if (!u.approved && !(u.email in this.pendingRole)) this.pendingRole[u.email] = 'general';
        }
      },
      error: () => this.usersError.set('Failed to load users (admin only).'),
    });
  }

  approve(u: AdminUser) {
    const role = this.pendingRole[u.email] || 'general';
    this.savingEmail.set(u.email);
    this.api.approveUser(u.email, role).subscribe({
      next: () => {
        u.approved = true;
        u.role = role;
        this.users.set([...this.users()]); // re-trigger computed split
        this.savingEmail.set('');
      },
      error: () => { this.savingEmail.set(''); this.usersError.set(`Failed to approve ${u.email}.`); },
    });
  }

  changeRole(u: AdminUser, role: string) {
    const prev = u.role;
    if (role === prev) return;
    u.role = role;                 // optimistic — keeps the <select> in sync
    this.savingEmail.set(u.email);
    this.api.updateUserRole(u.email, role).subscribe({
      next: () => this.savingEmail.set(''),
      error: () => {
        u.role = prev;
        this.savingEmail.set('');
        this.usersError.set(`Failed to update role for ${u.email}.`);
        this.loadUsers();
      },
    });
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
    this.syncMessage.set('Starting full sync (fetch + classify)…');
    this.api.triggerSync().subscribe({
      next: r => {
        if (r.status === 'already_running') {
          this.syncMessage.set('A sync is already running — watching progress…');
        } else if (r.status === 'error') {
          this.syncing.set(false);
          this.syncMessage.set(`Could not start sync: ${r.message ?? 'unknown error'}`);
          return;
        } else {
          this.syncMessage.set('Sync in progress… (fetching + classifying tickets)');
        }
        this.startSyncPolling();
      },
      error: () => {
        this.syncing.set(false);
        this.syncMessage.set('Could not start sync (request failed).');
      },
    });
  }

  private startSyncPolling() {
    this.stopSyncPolling();
    this.syncPoll = setInterval(() => {
      this.api.getSyncStatus().subscribe({
        next: s => {
          this.status.set(s);
          const job: SyncJob | undefined = s.job;
          if (!job || job.state === 'running') return;
          this.stopSyncPolling();
          this.syncing.set(false);
          if (job.state === 'done') {
            const r = job.result || {};
            const parts = [r.sync_summary, r.classify_summary].filter(Boolean).join(' · ');
            this.syncMessage.set(`✓ Sync complete${parts ? ' — ' + parts : ''}`);
          } else if (job.state === 'error') {
            this.syncMessage.set(`Sync failed: ${job.message || 'see logs'}`);
          }
        },
        error: () => { /* transient poll error — keep polling */ },
      });
    }, 5000);
  }

  private stopSyncPolling() {
    if (this.syncPoll) { clearInterval(this.syncPoll); this.syncPoll = null; }
  }

  ngOnDestroy() {
    this.stopSyncPolling();
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
