import { Component, input, OnDestroy, OnInit, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { inject } from '@angular/core';

interface ProgressItem {
  path: string;
  status: 'done' | 'error';
  label: string;
}

@Component({
  selector: 'app-execute-step',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="execute-step">
      <div class="execute-header">
        <h2>Ingesting: {{ filename() }}</h2>
        <span class="elapsed">⏱ {{ elapsedSeconds() }}s elapsed</span>
      </div>

      @if (!jobId() && !errorMsg()) {
        <div class="planning-spinner">
          <div class="spinner"></div>
          <p>Starting ingestion job…</p>
        </div>
      }

      @if (progressItems().length > 0) {
        <div class="progress-list">
          <div class="section-label">Progress</div>
          @for (item of progressItems(); track item.path + item.label) {
            <div class="progress-item" [class]="item.status">
              <span class="item-icon">{{ item.status === 'done' ? '✅' : '❌' }}</span>
              <span class="item-path">{{ item.path || item.label }}</span>
            </div>
          }
        </div>
      }

      @if (jobId() && !done() && !errorMsg()) {
        <div class="progress-item pending" style="color:#888;font-size:0.84em;margin-top:4px">
          ⏳ Running in background — you can safely switch tabs
        </div>
      }

      @if (total() > 0) {
        <div class="progress-bar">
          <div class="progress-fill" [style.width.%]="progressPercent()"></div>
        </div>
      }

      @if (done()) {
        <div class="success-box">
          <div class="success-title">
            ✅ Ingestion complete — {{ createdCount() }} created, {{ modifiedCount() }} modified
          </div>
          <div class="result-links">
            @for (link of resultLinks(); track link) {
              <a routerLink="/ask" [queryParams]="{q: link}" class="result-link">{{ link }}</a>
            }
          </div>
        </div>
        <button class="btn-primary" (click)="ingestAnother.emit()">Ingest another doc</button>
      }

      @if (errorMsg()) {
        <div class="error-box">
          <div class="error-title">❌ Ingestion failed</div>
          <div class="error-detail">{{ errorMsg() }}</div>
        </div>
        <button class="btn-secondary" (click)="ingestAnother.emit()">Go back</button>
      }
    </div>
  `,
})
export class ExecuteStep implements OnInit, OnDestroy {
  private api = inject(ApiService);

  sessionId = input.required<string>();
  filename = input<string>('');
  ingestAnother = output<void>();

  jobId = signal('');
  progressItems = signal<ProgressItem[]>([]);
  seenPaths = new Set<string>();
  total = signal(0);
  completed = signal(0);
  done = signal(false);
  errorMsg = signal('');
  resultLinks = signal<string[]>([]);
  createdCount = signal(0);
  modifiedCount = signal(0);
  elapsedSeconds = signal(0);

  private startSub?: Subscription;
  private pollHandle?: ReturnType<typeof setInterval>;
  private timerHandle?: ReturnType<typeof setInterval>;
  private startedAt = Date.now();

  progressPercent(): number {
    const t = this.total();
    return t > 0 ? Math.round((this.completed() / t) * 100) : 0;
  }

  ngOnInit() {
    this.startedAt = Date.now();
    this.timerHandle = setInterval(() => {
      this.elapsedSeconds.set(Math.round((Date.now() - this.startedAt) / 1000));
    }, 1000);

    this.startSub = this.api.startIngestJob(this.sessionId()).subscribe({
      next: (resp) => {
        this.jobId.set(resp.job_id);
        this.startPolling(resp.job_id);
      },
      error: (err: { error?: { detail?: string } }) => {
        this.errorMsg.set(err?.error?.detail ?? 'Failed to start ingestion job.');
        this.stopTimers();
      },
    });
  }

  ngOnDestroy() {
    this.startSub?.unsubscribe();
    this.stopTimers();
  }

  private startPolling(jobId: string) {
    this.pollHandle = setInterval(() => {
      this.api.getIngestJob(jobId).subscribe({
        next: (job) => this.applyJobState(job),
        error: () => { /* poll again next tick */ },
      });
    }, 2000);
  }

  private applyJobState(job: { status: string; events: Array<{ type: string; tool: string; path: string; status: string; result: Record<string, unknown>; completed: number; total: number }>; files_created: string[]; files_modified: string[]; links: string[]; error_msg: string }) {
    // Append only new events (avoid duplicating items already shown)
    for (const evt of job.events) {
      if (evt.type === 'progress') {
        this.total.set(evt.total);
        this.completed.set(evt.completed);
        const key = evt.path || evt.tool;
        if (!this.seenPaths.has(key)) {
          this.seenPaths.add(key);
          const items = [...this.progressItems()];
          items.push({
            path: evt.path,
            status: evt.status === 'error' ? 'error' : 'done',
            label: `${evt.tool}: ${evt.path}`,
          });
          this.progressItems.set(items);
        }
      }
    }

    if (job.status === 'complete') {
      this.done.set(true);
      this.resultLinks.set(job.links);
      this.createdCount.set(job.files_created.length);
      this.modifiedCount.set(job.files_modified.length);
      this.stopTimers();
    } else if (job.status === 'error') {
      this.errorMsg.set(job.error_msg || 'Ingestion failed.');
      this.stopTimers();
    }
  }

  private stopTimers() {
    if (this.pollHandle) { clearInterval(this.pollHandle); this.pollHandle = undefined; }
    if (this.timerHandle) { clearInterval(this.timerHandle); this.timerHandle = undefined; }
  }
}
