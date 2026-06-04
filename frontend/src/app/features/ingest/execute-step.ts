import { Component, input, OnDestroy, OnInit, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { ApiService, IngestProgressEvent } from '../../core/api.service';
import { inject } from '@angular/core';

interface ProgressItem {
  path: string;
  status: 'pending' | 'in_progress' | 'done' | 'error';
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

      <div class="progress-list">
        <div class="section-label">Progress</div>
        @for (item of progressItems(); track item.path + item.label) {
          <div class="progress-item" [class]="item.status">
            <span class="item-icon">
              @switch (item.status) {
                @case ('done') { ✅ }
                @case ('error') { ❌ }
                @case ('in_progress') { ⏳ }
                @default { ○ }
              }
            </span>
            <span class="item-path">{{ item.path || item.label }}</span>
          </div>
        }
      </div>

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
              <a routerLink="/ask" [queryParams]="{q: link}" class="result-link">
                {{ link }}
              </a>
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

      @if (!done() && !errorMsg()) {
        <div class="warning-note">⚠ Ingestion in progress — please don't close this tab</div>
      }
    </div>
  `,
})
export class ExecuteStep implements OnInit, OnDestroy {
  private api = inject(ApiService);

  sessionId = input.required<string>();
  filename = input<string>('');
  ingestAnother = output<void>();

  progressItems = signal<ProgressItem[]>([]);
  total = signal(0);
  completed = signal(0);
  done = signal(false);
  errorMsg = signal('');
  resultLinks = signal<string[]>([]);
  createdCount = signal(0);
  modifiedCount = signal(0);
  elapsedSeconds = signal(0);

  private sub?: Subscription;
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

    this.sub = this.api.streamExecuteIngest(this.sessionId()).subscribe({
      next: (evt: IngestProgressEvent) => this.handleEvent(evt),
      error: (err: unknown) => this.errorMsg.set(String((err as Error)?.message ?? err)),
    });
  }

  ngOnDestroy() {
    this.sub?.unsubscribe();
    if (this.timerHandle) clearInterval(this.timerHandle);
  }

  private handleEvent(evt: IngestProgressEvent) {
    switch (evt.type) {
      case 'progress': {
        this.total.set(evt.total);
        this.completed.set(evt.completed);
        const items = [...this.progressItems()];
        const idx = items.findIndex(i => i.path === evt.path && i.status === 'pending');
        const newItem: ProgressItem = {
          path: evt.path,
          status: evt.status === 'error' ? 'error' : 'done',
          label: `${evt.tool}: ${evt.path}`,
        };
        if (idx >= 0) items[idx] = newItem;
        else items.push(newItem);
        this.progressItems.set(items);
        break;
      }
      case 'complete': {
        this.done.set(true);
        this.resultLinks.set(evt.links);
        this.createdCount.set(evt.files_created.length);
        this.modifiedCount.set(evt.files_modified.length);
        if (this.timerHandle) clearInterval(this.timerHandle);
        break;
      }
      case 'error':
      case '__sse_error': {
        const msg = (evt as { message?: string; error?: string }).message
          ?? (evt as { message?: string; error?: string }).error
          ?? 'Unknown error';
        this.errorMsg.set(msg);
        if (this.timerHandle) clearInterval(this.timerHandle);
        break;
      }
    }
  }
}
