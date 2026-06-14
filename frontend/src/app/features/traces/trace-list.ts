import { Component, signal, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Subject, Subscription, debounceTime, distinctUntilChanged } from 'rxjs';
import {
  ApiService,
  TraceSessionSummary,
  TraceListParams,
} from '../../core/api.service';

const PAGE_SIZE = 25;

@Component({
  selector: 'app-trace-list',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page">
      <header class="page-header">
        <h1>Traces</h1>
        <button class="refresh-btn" (click)="onRefresh()">↻</button>
      </header>

      <section class="section">
        <!-- Filter bar -->
        <div class="filter-bar">
          <input
            class="search-input"
            type="text"
            placeholder="Search question…"
            [ngModel]="searchQuery()"
            (ngModelChange)="onSearchInput($event)"
          />
          <label class="filter-group">
            mode
            <select
              [ngModel]="modeFilter()"
              (ngModelChange)="modeFilter.set($event); onFilterChange()"
            >
              <option value="all">all</option>
              <option value="api">api</option>
              <option value="claude-code">claude-code</option>
            </select>
          </label>
          <label class="filter-group">
            status
            <select
              [ngModel]="statusFilter()"
              (ngModelChange)="statusFilter.set($event); onFilterChange()"
            >
              <option value="all">all</option>
              <option value="success">success</option>
              <option value="error">error</option>
              <option value="rejected">rejected</option>
              <option value="client_disconnect">disconnect</option>
            </select>
          </label>
          <label class="filter-group">
            range
            <select
              [ngModel]="rangeFilter()"
              (ngModelChange)="rangeFilter.set($event); onFilterChange()"
            >
              <option value="24h">24h</option>
              <option value="7d">7d</option>
              <option value="30d">30d</option>
              <option value="all">all</option>
            </select>
          </label>
          <label class="filter-check">
            <input
              type="checkbox"
              [ngModel]="includeOrphaned()"
              (ngModelChange)="includeOrphaned.set($event); onFilterChange()"
            />
            orphaned
          </label>
        </div>

        <!-- Loading -->
        @if (loading()) {
          <p class="loading-text">Loading…</p>
        }

        <!-- Error -->
        @if (!loading() && error()) {
          <div class="error-state">
            <span>{{ error() }}</span>
            <button class="retry-btn" (click)="onRefresh()">Retry</button>
          </div>
        }

        <!-- Table / empty state -->
        @if (!loading() && !error()) {
          @if (traces().length === 0) {
            <div class="empty-state">
              <p>No traces match these filters.</p>
              <button class="reset-btn" (click)="onResetFilters()">Reset filters</button>
            </div>
          } @else {
            <div class="table-wrap">
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>Started (UTC)</th>
                    <th>User</th>
                    <th>Question</th>
                    <th>Mode</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Tokens</th>
                    <th>Cost</th>
                    <th>Tools</th>
                  </tr>
                </thead>
                <tbody>
                  @for (trace of traces(); track trace.trace_id) {
                    <tr class="trace-row" (click)="onRowClick(trace.trace_id)">
                      <td class="col-date">{{ formatDate(trace.started_at) }}</td>
                      <td class="col-user" [title]="trace.user_email || ''">{{ formatUser(trace.user_email) }}</td>
                      <td class="col-question">{{ truncate(trace.question) }}</td>
                      <td class="col-mode"><code>{{ trace.mode }}</code></td>
                      <td class="col-status">
                        <span class="status-chip" [ngClass]="statusClass(trace.status)">
                          {{ statusLabel(trace.status) }}
                        </span>
                      </td>
                      <td class="col-num">{{ formatDuration(trace.duration_ms) }}</td>
                      <td class="col-num">{{ formatTokens(trace.total_tokens_input, trace.total_tokens_output) }}</td>
                      <td class="col-cost">
                        @if (trace.total_cost_usd === null) {
                          <span class="cost-null" title="claude-code billing is external">—</span>
                        } @else {
                          {{ formatCost(trace.total_cost_usd) }}
                        }
                      </td>
                      <td class="col-num">{{ trace.tool_call_count }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>

            <div class="pagination">
              <button class="page-btn" (click)="onPrevPage()" [disabled]="!hasPrev">← Prev</button>
              <span class="page-label">{{ pageLabel }}</span>
              <button class="page-btn" (click)="onNextPage()" [disabled]="!hasNext">Next →</button>
            </div>
          }
        }
      </section>
    </div>
  `,
  styleUrl: './trace-list.scss',
})
export class TraceList implements OnInit, OnDestroy {
  private api = inject(ApiService);
  private router = inject(Router);

  // Filter signals
  searchQuery = signal('');
  modeFilter = signal('all');
  statusFilter = signal('all');
  rangeFilter = signal('7d');
  includeOrphaned = signal(false);

  // State signals
  traces = signal<TraceSessionSummary[]>([]);
  total = signal(0);
  limit = signal(PAGE_SIZE);
  offset = signal(0);
  loading = signal(false);
  error = signal('');

  private search$ = new Subject<string>();
  private subs = new Subscription();

  ngOnInit() {
    this.subs.add(
      this.search$
        .pipe(debounceTime(300), distinctUntilChanged())
        .subscribe(() => this.onFilterChange())
    );
    this.loadTraces();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  loadTraces() {
    this.loading.set(true);
    this.error.set('');

    const params: TraceListParams = {
      limit: this.limit(),
      offset: this.offset(),
    };
    if (this.modeFilter() !== 'all') params.mode = this.modeFilter();
    if (this.statusFilter() !== 'all') params.status = this.statusFilter();
    if (this.searchQuery().trim()) params.search = this.searchQuery().trim();
    if (this.includeOrphaned()) params.include_orphaned = true;
    const since = this.rangeToSince(this.rangeFilter());
    if (since) params.since = since;

    this.api.listTraces(params).subscribe({
      next: data => {
        this.traces.set(data.sessions);
        this.total.set(data.total);
        this.loading.set(false);
      },
      error: err => {
        this.error.set(err?.error?.detail ?? 'Failed to load traces');
        this.loading.set(false);
      },
    });
  }

  onFilterChange() {
    this.offset.set(0);
    this.loadTraces();
  }

  onSearchInput(value: string) {
    this.searchQuery.set(value);
    this.search$.next(value);
  }

  onRowClick(traceId: string) {
    this.router.navigate(['/traces', traceId]);
  }

  onRefresh() {
    this.loadTraces();
  }

  onPrevPage() {
    this.offset.set(Math.max(0, this.offset() - this.limit()));
    this.loadTraces();
  }

  onNextPage() {
    this.offset.set(this.offset() + this.limit());
    this.loadTraces();
  }

  onResetFilters() {
    this.searchQuery.set('');
    this.modeFilter.set('all');
    this.statusFilter.set('all');
    this.rangeFilter.set('7d');
    this.includeOrphaned.set(false);
    this.offset.set(0);
    this.loadTraces();
  }

  // ── Display helpers ──────────────────────────────────────────────────────

  statusClass(status: string): string {
    const map: Record<string, string> = {
      success: 'chip-success',
      error: 'chip-error',
      rejected: 'chip-warning',
      client_disconnect: 'chip-info',
      orphaned: 'chip-orphaned',
    };
    return map[status] ?? 'chip-unknown';
  }

  statusLabel(status: string): string {
    return status === 'client_disconnect' ? 'disconnect' : status;
  }

  formatDate(iso: string | null): string {
    if (!iso) return '—';
    const d = new Date(iso);
    const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
    const dd = String(d.getUTCDate()).padStart(2, '0');
    const hh = String(d.getUTCHours()).padStart(2, '0');
    const min = String(d.getUTCMinutes()).padStart(2, '0');
    return `${mm}-${dd} ${hh}:${min}`;
  }

  formatCost(cost: number | null): string {
    if (cost === null) return '—';
    return cost < 1 ? `$${cost.toFixed(4)}` : `$${cost.toFixed(2)}`;
  }

  formatDuration(ms: number | null): string {
    if (ms === null) return '—';
    return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
  }

  formatTokens(input: number | null, output: number | null): string {
    if (input === null && output === null) return '—';
    const total = (input ?? 0) + (output ?? 0);
    return total >= 1000 ? `${(total / 1000).toFixed(1)}k` : String(total);
  }

  truncate(s: string | null, len = 70): string {
    if (!s) return '—';
    return s.length > len ? s.slice(0, len) + '…' : s;
  }

  /** Show the local-part of the email (before @) to keep the column compact;
   *  full address is the title on hover. */
  formatUser(email: string | null): string {
    if (!email) return '—';
    const at = email.indexOf('@');
    return at > 0 ? email.slice(0, at) : email;
  }

  get hasPrev(): boolean {
    return this.offset() > 0;
  }

  get hasNext(): boolean {
    return this.total() > this.offset() + this.limit();
  }

  get pageLabel(): string {
    if (this.total() === 0) return '0 results';
    const start = this.offset() + 1;
    const end = Math.min(this.offset() + this.limit(), this.total());
    return `${start}–${end} of ${this.total()}`;
  }

  private rangeToSince(range: string): string | undefined {
    if (range === 'all') return undefined;
    const hours = range === '24h' ? 24 : range === '7d' ? 168 : 720;
    return new Date(Date.now() - hours * 3_600_000).toISOString();
  }
}
