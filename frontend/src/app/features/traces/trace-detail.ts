import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService, TraceDetail as TraceDetailData, TraceEvent } from '../../core/api.service';

interface RoundGroup {
  round: number;
  label: string;
  events: TraceEvent[];
}

@Component({
  selector: 'app-trace-detail',
  imports: [CommonModule],
  template: `
    <div class="page">
      <!-- Loading -->
      @if (loading()) {
        <p class="loading-text">Loading trace…</p>
      }

      <!-- Error -->
      @if (!loading() && error()) {
        <div class="error-state">
          <span>{{ error() }}</span>
          <button class="back-btn" (click)="goBack()">← Back to traces</button>
        </div>
      }

      @if (!loading() && !error() && detail()) {
        <!-- A. Header -->
        <header class="page-header">
          <button class="back-link" (click)="goBack()">← Traces</button>
          <div class="header-main">
            <div class="trace-id-row">
              <h1 class="trace-id" [title]="detail()!.session.trace_id">
                Trace {{ detail()!.session.trace_id | slice:0:8 }}…
              </h1>
              <button
                class="copy-btn"
                (click)="copyTraceId(detail()!.session.trace_id)"
                [title]="'Copy full trace ID: ' + detail()!.session.trace_id"
                aria-label="Copy trace ID"
              >{{ copySuccess() ? '✓ copied' : '⎘ copy' }}</button>
              <span class="status-chip" [ngClass]="statusClass(detail()!.session.status)">
                {{ statusLabel(detail()!.session.status) }}
              </span>
            </div>
          </div>
        </header>

        <!-- B. Summary row -->
        <section class="summary-section">
          <div class="summary-grid">
            <div class="summary-item">
              <span class="summary-label">Mode</span>
              <code class="mode-chip">{{ detail()!.session.mode }}</code>
            </div>
            <div class="summary-item">
              <span class="summary-label">Rounds</span>
              <span class="summary-value">{{ detail()!.session.round_count }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Tools</span>
              <span class="summary-value">{{ detail()!.session.tool_call_count }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Tokens</span>
              <span class="summary-value mono">{{ formatTokenPair(detail()!.session.total_tokens_input, detail()!.session.total_tokens_output) }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Cost</span>
              @if (detail()!.session.total_cost_usd === null) {
                <span class="summary-value muted" title="claude-code billing is external">—</span>
              } @else {
                <span class="summary-value mono">{{ formatCost(detail()!.session.total_cost_usd) }}</span>
              }
            </div>
            <div class="summary-item">
              <span class="summary-label">Duration</span>
              <span class="summary-value mono">{{ formatDuration(detail()!.session.duration_ms) }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">Started</span>
              <span class="summary-value mono">{{ formatDate(detail()!.session.started_at) }}</span>
            </div>
          </div>
          @if (detail()!.session.conversation_id) {
            <button class="conv-link" (click)="openConversation(detail()!.session.conversation_id!)">
              → Open conversation
            </button>
          }
        </section>

        <!-- E. Rejected special case banner -->
        @if (detail()!.session.status === 'rejected') {
          <section class="rejected-banner">
            <strong>Rejected</strong>
            @if (rejectedInfo()) {
              — HTTP {{ rejectedInfo()!.code }} — {{ rejectedInfo()!.reason }}
            } @else if (detail()!.session.error_message) {
              — {{ detail()!.session.error_message }}
            }
          </section>
        }

        <!-- C. Timeline -->
        <section class="timeline-section">
          <h2 class="section-heading">Timeline</h2>
          @if (detail()!.events.length === 0) {
            <p class="empty-text">No events recorded for this trace.</p>
          } @else {
            @for (group of groupedEvents(); track group.round) {
              <div class="round-group">
                <div class="round-label">{{ group.label }}</div>
                @for (ev of group.events; track ev.event_id) {
                  <div
                    class="event-row"
                    [class.event-error]="ev.status === 'error'"
                    [class.event-expanded]="isExpanded(ev.event_id)"
                    [attr.aria-expanded]="isExpanded(ev.event_id)"
                    tabindex="0"
                    (click)="toggleEvent(ev.event_id)"
                    (keydown.enter)="toggleEvent(ev.event_id)"
                    (keydown.space)="$event.preventDefault(); toggleEvent(ev.event_id)"
                  >
                    <div class="event-main">
                      <span class="event-seq">s{{ ev.sequence }}·r{{ ev.round_num ?? 0 }}</span>
                      <span class="event-type">
                        {{ ev.component }}<span class="sep">/</span>{{ ev.event_type }}
                        @if (ev.tool_name) {
                          <span class="tool-name">{{ ev.tool_name }}</span>
                        }
                        @if (isSynthesis(ev)) {
                          <span class="tag-synthesis">synthesis</span>
                        }
                        @if (ev.status === 'error') {
                          <span class="tag-error">error</span>
                        }
                      </span>
                      <div class="bar-track" role="presentation">
                        <div
                          class="bar-fill"
                          [class.bar-error]="ev.status === 'error'"
                          [style.width]="barWidth(ev.duration_ms)"
                        ></div>
                      </div>
                      <span class="event-dur">{{ formatDuration(ev.duration_ms) }}</span>
                    </div>

                    <!-- Expanded details -->
                    @if (isExpanded(ev.event_id)) {
                      <div class="event-details" role="region" [attr.aria-label]="'Details for event ' + ev.sequence">
                        @if (ev.tool_input_json) {
                          <div class="detail-row">
                            <span class="detail-label">Input</span>
                            <pre class="detail-pre">{{ ev.tool_input_json }}</pre>
                          </div>
                        }
                        @if (ev.tool_output_summary) {
                          <div class="detail-row">
                            <span class="detail-label">Output</span>
                            <pre class="detail-pre">{{ ev.tool_output_summary }}</pre>
                          </div>
                        }
                        @if (ev.status === 'error') {
                          <div class="detail-row">
                            <span class="detail-label">Error</span>
                            <pre class="detail-pre error-pre">{{ errorDetails(ev) }}</pre>
                          </div>
                        }
                        @if (ev.metadata_json) {
                          <div class="detail-row">
                            <span class="detail-label">Metadata</span>
                            <pre class="detail-pre">{{ ev.metadata_json }}</pre>
                          </div>
                        }
                        @if (!ev.tool_input_json && !ev.tool_output_summary && !ev.metadata_json) {
                          <span class="detail-empty">No additional details.</span>
                        }
                      </div>
                    }
                  </div>
                }
              </div>
            }
          }
        </section>

        <!-- D. Breakdown -->
        @if (detail()!.metrics) {
          <section class="breakdown-section">
            <h2 class="section-heading">Breakdown</h2>
            <div class="breakdown-bars">
              <div class="breakdown-row">
                <span class="breakdown-label">LLM</span>
                <div class="breakdown-track">
                  <div class="breakdown-fill fill-llm" [style.width]="bpct(detail()!.metrics!.latency_llm_ms, detail()!.metrics!.latency_total_ms) + '%'"></div>
                </div>
                <span class="breakdown-value mono">
                  {{ formatDuration(detail()!.metrics!.latency_llm_ms) }}
                  <span class="pct-label">({{ bpct(detail()!.metrics!.latency_llm_ms, detail()!.metrics!.latency_total_ms) }}%)</span>
                </span>
              </div>
              <div class="breakdown-row">
                <span class="breakdown-label">Tools</span>
                <div class="breakdown-track">
                  <div class="breakdown-fill fill-tools" [style.width]="bpct(detail()!.metrics!.latency_tools_ms, detail()!.metrics!.latency_total_ms) + '%'"></div>
                </div>
                <span class="breakdown-value mono">
                  {{ formatDuration(detail()!.metrics!.latency_tools_ms) }}
                  <span class="pct-label">({{ bpct(detail()!.metrics!.latency_tools_ms, detail()!.metrics!.latency_total_ms) }}%)</span>
                </span>
              </div>
              <div class="breakdown-row">
                <span class="breakdown-label">Preflight</span>
                <div class="breakdown-track">
                  <div class="breakdown-fill fill-preflight" [style.width]="bpct(detail()!.metrics!.latency_preflight_ms, detail()!.metrics!.latency_total_ms) + '%'"></div>
                </div>
                <span class="breakdown-value mono">
                  {{ formatDuration(detail()!.metrics!.latency_preflight_ms) }}
                  <span class="pct-label">({{ bpct(detail()!.metrics!.latency_preflight_ms, detail()!.metrics!.latency_total_ms) }}%)</span>
                </span>
              </div>
            </div>
          </section>
        }
      }
    </div>
  `,
  styleUrl: './trace-detail.scss',
})
export class TraceDetail implements OnInit {
  private api = inject(ApiService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  detail = signal<TraceDetailData | null>(null);
  loading = signal(true);
  error = signal('');
  copySuccess = signal(false);
  expandedEvents = signal(new Set<string>());

  ngOnInit() {
    const traceId = this.route.snapshot.paramMap.get('traceId');
    if (!traceId) {
      this.error.set('No trace ID in route.');
      this.loading.set(false);
      return;
    }
    this.loadTrace(traceId);
  }

  private loadTrace(traceId: string) {
    this.api.getTrace(traceId).subscribe({
      next: data => {
        this.detail.set(data);
        this.loading.set(false);
      },
      error: err => {
        const status = err?.status;
        this.error.set(
          status === 404
            ? `Trace not found: ${traceId}`
            : (err?.error?.detail ?? 'Failed to load trace')
        );
        this.loading.set(false);
      },
    });
  }

  // ── Navigation ────────────────────────────────────────────────────────────

  goBack() {
    this.router.navigate(['/traces']);
  }

  openConversation(conversationId: string) {
    this.router.navigate(['/ask'], { queryParams: { conversation_id: conversationId } });
  }

  // ── Interaction ───────────────────────────────────────────────────────────

  toggleEvent(eventId: string) {
    const s = new Set(this.expandedEvents());
    if (s.has(eventId)) s.delete(eventId); else s.add(eventId);
    this.expandedEvents.set(s);
  }

  isExpanded(eventId: string): boolean {
    return this.expandedEvents().has(eventId);
  }

  copyTraceId(traceId: string) {
    navigator.clipboard.writeText(traceId).then(() => {
      this.copySuccess.set(true);
      setTimeout(() => this.copySuccess.set(false), 2000);
    });
  }

  // ── Derived data ──────────────────────────────────────────────────────────

  groupedEvents(): RoundGroup[] {
    const d = this.detail();
    if (!d) return [];

    const map = new Map<number, TraceEvent[]>();
    for (const ev of d.events) {
      const r = ev.round_num ?? 0;
      if (!map.has(r)) map.set(r, []);
      map.get(r)!.push(ev);
    }

    return Array.from(map.entries())
      .sort(([a], [b]) => a - b)
      .map(([round, events]) => ({
        round,
        label: round === 0 ? 'Preflight' : `Round ${round}`,
        events,
      }));
  }

  rejectedInfo(): { code: string; reason: string } | null {
    const d = this.detail();
    if (!d || d.session.status !== 'rejected') return null;
    const ev = d.events.find(e => e.event_type === 'request_rejected' || e.event_type === 'request_end');
    if (!ev?.metadata_json) return null;
    try {
      const meta = JSON.parse(ev.metadata_json);
      const code = meta['status_code'] ?? meta['http_status'];
      const reason = meta['reason'] ?? meta['message'] ?? '';
      return code ? { code: String(code), reason: String(reason) } : null;
    } catch { return null; }
  }

  isSynthesis(ev: TraceEvent): boolean {
    if (ev.event_type !== 'llm_response') return false;
    if (!ev.metadata_json) return false;
    try {
      return JSON.parse(ev.metadata_json)?.is_synthesis === true;
    } catch { return false; }
  }

  errorDetails(ev: TraceEvent): string {
    if (!ev.metadata_json) return ev.status ?? 'error';
    try {
      const m = JSON.parse(ev.metadata_json);
      const type = m['exception_type'] ?? 'Error';
      const msg = m['exception_message'] ?? '';
      return msg ? `${type}: ${msg}` : type;
    } catch { return 'error'; }
  }

  barWidth(ms: number | null): string {
    const total = this.detail()?.session.duration_ms;
    if (!ms || !total) return '2%';
    return `${Math.max(2, Math.min(100, (ms / total) * 100)).toFixed(1)}%`;
  }

  bpct(ms: number | null, total: number | null): number {
    if (!ms || !total) return 0;
    return Math.round((ms / total) * 100);
  }

  // ── Display helpers ───────────────────────────────────────────────────────

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
    return `${mm}-${dd} ${hh}:${min} UTC`;
  }

  formatCost(cost: number | null): string {
    if (cost === null) return '—';
    return cost < 1 ? `$${cost.toFixed(4)}` : `$${cost.toFixed(2)}`;
  }

  formatDuration(ms: number | null): string {
    if (ms === null) return '—';
    return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
  }

  formatTokenPair(input: number | null, output: number | null): string {
    const fmt = (n: number | null) =>
      n === null ? '—' : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
    return `${fmt(input)} → ${fmt(output)}`;
  }
}
