import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs';
import { BaseChartDirective } from 'ng2-charts';
import type { ChartConfiguration, ChartData } from 'chart.js';
import {
  ApiService,
  TraceOverview,
  TraceToolsResponse,
  TraceErrorsResponse,
  TraceCostResponse,
} from '../../core/api.service';

// Design-token colors (CSS vars read at build time; these match styles.scss)
const C_ACCENT   = '#1e293b';
const C_INFO     = '#1e40af';
const C_SUCCESS  = '#15803d';
const C_WARNING  = '#92400e';
const C_BORDER   = '#e7e5e4';
const C_MUTED    = '#a8a29e';

const RANGES = [
  { value: '24h', label: '24h' },
  { value: '7d',  label: '7d'  },
  { value: '30d', label: '30d' },
  { value: 'all', label: 'All' },
];

@Component({
  selector: 'app-trace-dashboard',
  imports: [CommonModule, BaseChartDirective],
  template: `
    <div class="page">
      <!-- Header -->
      <header class="page-header">
        <h1>Observability Dashboard</h1>
        <div class="header-actions">
          <div class="range-tabs">
            @for (r of ranges; track r.value) {
              <button
                class="range-tab"
                [class.active]="timeRange() === r.value"
                (click)="setRange(r.value)"
              >{{ r.label }}</button>
            }
          </div>
          <button class="refresh-btn" (click)="loadAll()">↻</button>
        </div>
      </header>

      @if (loading()) {
        <p class="loading-text">Loading…</p>
      }

      @if (!loading()) {

        <!-- Section errors -->
        @if (hasErrors()) {
          <div class="section-errors">
            @for (e of errorEntries(); track e[0]) {
              <span class="section-error-badge">{{ e[0] }}: {{ e[1] }}</span>
            }
          </div>
        }

        <!-- Metric cards -->
        @if (overview()) {
          <div class="metric-cards">
            <div class="metric-card">
              <div class="metric-label">Queries</div>
              <div class="metric-value">{{ overview()!.total_queries | number }}</div>
              <div class="metric-sub">in {{ timeRange() }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">Success rate</div>
              <div class="metric-value" [class.value-success]="successRateNum() >= 95" [class.value-warn]="successRateNum() < 80">
                {{ successRate() }}
              </div>
              <div class="metric-sub">{{ statusCount('success') }} successful</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">Avg latency</div>
              <div class="metric-value">{{ formatDuration(overview()!.latency_ms.avg) }}</div>
              <div class="metric-sub">p50 {{ formatDuration(overview()!.latency_ms.p50) }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">Total cost</div>
              <div class="metric-value mono">{{ formatCost(overview()!.total_cost_usd) }}</div>
              <div class="metric-sub">claude-code billed externally</div>
            </div>
          </div>

          <!-- Latency gauges -->
          <section class="section gauges-section">
            <h2 class="section-heading">Latency Percentiles</h2>
            <div class="gauges-row">
              <div class="gauge">
                <div class="gauge-label">p50</div>
                <div class="gauge-value mono">{{ formatDuration(overview()!.latency_ms.p50) }}</div>
              </div>
              <div class="gauge-divider"></div>
              <div class="gauge">
                <div class="gauge-label">p95</div>
                <div class="gauge-value mono" [class.gauge-warn]="isSlowP95()">{{ formatDuration(overview()!.latency_ms.p95) }}</div>
              </div>
              <div class="gauge-divider"></div>
              <div class="gauge">
                <div class="gauge-label">p99</div>
                <div class="gauge-value mono" [class.gauge-warn]="isSlowP99()">{{ formatDuration(overview()!.latency_ms.p99) }}</div>
              </div>
            </div>
          </section>
        }

        <!-- Charts grid: cost line + mode pie -->
        <div class="charts-grid">
          <!-- Cost by day -->
          <section class="section chart-card">
            <h2 class="section-heading">Cost by Day</h2>
            @if (cost() && cost()!.cost_by_day.length > 0) {
              <div class="chart-canvas-wrap">
                <canvas baseChart
                  [type]="'line'"
                  [data]="costLineData()"
                  [options]="costLineOptions"
                  [legend]="false"
                ></canvas>
              </div>
              <div class="cost-meta">
                @if (cost()!.cache_hit_rate !== null) {
                  <span class="meta-chip">Cache hit {{ (cost()!.cache_hit_rate! * 100).toFixed(1) }}%</span>
                }
                <span class="meta-chip">{{ (cost()!.tokens.input / 1000).toFixed(0) }}k in / {{ (cost()!.tokens.output / 1000).toFixed(0) }}k out</span>
              </div>
            } @else {
              <p class="empty-text">No cost data for this period.</p>
            }
          </section>

          <!-- Mode split pie -->
          <section class="section chart-card chart-small">
            <h2 class="section-heading">Mode Split</h2>
            @if (overview() && hasModeSplit()) {
              <div class="chart-canvas-wrap chart-canvas-pie">
                <canvas baseChart
                  [type]="'pie'"
                  [data]="modePieData()"
                  [options]="modePieOptions"
                  [legend]="true"
                ></canvas>
              </div>
            } @else {
              <p class="empty-text">No mode data.</p>
            }
          </section>
        </div>

        <!-- Tool usage horizontal bar chart -->
        @if (tools() && tools()!.tools.length > 0) {
          <section class="section chart-card chart-full">
            <h2 class="section-heading">Top Tools</h2>
            <div class="chart-canvas-wrap chart-canvas-tall">
              <canvas baseChart
                [type]="'bar'"
                [data]="toolBarData()"
                [options]="toolBarOptions"
                [legend]="false"
              ></canvas>
            </div>
          </section>
        }

        <!-- Tables row -->
        <div class="tables-grid">
          <!-- Per-tool stats -->
          <section class="section">
            <h2 class="section-heading">Tool Stats</h2>
            @if (tools() && tools()!.tools.length > 0) {
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>Tool</th>
                    <th class="num-col">Calls</th>
                    <th class="num-col">Avg dur.</th>
                    <th class="num-col">Error %</th>
                  </tr>
                </thead>
                <tbody>
                  @for (tool of sortedTools(); track tool.tool_name) {
                    <tr>
                      <td><code class="tool-name">{{ tool.tool_name }}</code></td>
                      <td class="num-col">{{ tool.call_count }}</td>
                      <td class="num-col">{{ formatDuration(tool.avg_duration_ms) }}</td>
                      <td class="num-col" [class.cell-error]="tool.error_rate_pct > 10">
                        {{ tool.error_rate_pct.toFixed(1) }}%
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            } @else {
              <p class="empty-text">No tool data for this period.</p>
            }
          </section>

          <!-- Recent errors -->
          <section class="section">
            <h2 class="section-heading">Recent Errors</h2>
            @if (errors() && errors()!.recent_exceptions.length > 0) {
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Type</th>
                    <th>Where</th>
                    <th>Message</th>
                  </tr>
                </thead>
                <tbody>
                  @for (ex of errors()!.recent_exceptions; track ex.trace_id + ex.timestamp) {
                    <tr>
                      <td class="col-date">
                        <button class="trace-link" (click)="goToTrace(ex.trace_id)">
                          {{ formatDate(ex.timestamp) }}
                        </button>
                      </td>
                      <td><code class="exc-type">{{ ex.exception_type }}</code></td>
                      <td class="col-where">{{ ex.where ?? '—' }}</td>
                      <td class="col-message">{{ truncate(ex.exception_message, 80) }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            } @else {
              <p class="empty-text">No recent errors. ✓</p>
            }
          </section>
        </div>

      } <!-- end !loading -->
    </div>
  `,
  styleUrl: './dashboard.scss',
})
export class Dashboard implements OnInit {
  private api = inject(ApiService);
  private router = inject(Router);

  readonly ranges = RANGES;

  // State
  loading = signal(true);
  timeRange = signal('7d');
  overview = signal<TraceOverview | null>(null);
  tools = signal<TraceToolsResponse | null>(null);
  errors = signal<TraceErrorsResponse | null>(null);
  cost = signal<TraceCostResponse | null>(null);
  sectionErrors = signal<Record<string, string>>({});

  // Chart data signals — new object references force ng2-charts ngOnChanges
  toolBarData = signal<ChartData<'bar'>>({ datasets: [] });
  modePieData = signal<ChartData<'pie'>>({ datasets: [] });
  costLineData = signal<ChartData<'line'>>({ datasets: [] });

  // ── Static chart options ──────────────────────────────────────────────────

  readonly toolBarOptions: ChartConfiguration<'bar'>['options'] = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { mode: 'index' } },
    scales: {
      x: { beginAtZero: true, grid: { color: C_BORDER }, ticks: { color: C_MUTED } },
      y: { grid: { display: false }, ticks: { color: C_MUTED, font: { family: 'monospace', size: 11 } } },
    },
  };

  readonly modePieOptions: ChartConfiguration<'pie'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { color: C_MUTED, padding: 16, font: { size: 12 } } },
    },
  };

  readonly costLineOptions: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: ctx => `$${(ctx.parsed.y as number).toFixed(4)}`,
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: C_BORDER },
        ticks: { color: C_MUTED, callback: v => `$${Number(v).toFixed(3)}` },
      },
      x: { grid: { display: false }, ticks: { color: C_MUTED } },
    },
  };

  ngOnInit() {
    this.loadAll();
  }

  setRange(value: string) {
    this.timeRange.set(value);
    this.loadAll();
  }

  loadAll() {
    this.loading.set(true);
    const errs: Record<string, string> = {};
    const range = this.timeRange();

    forkJoin({
      overview: this.api.traceOverview(range).pipe(
        catchError(e => { errs['overview'] = e?.error?.detail ?? 'Load failed'; return of(null); })
      ),
      tools: this.api.traceTools(range).pipe(
        catchError(e => { errs['tools'] = e?.error?.detail ?? 'Load failed'; return of(null); })
      ),
      errors: this.api.traceErrors(range).pipe(
        catchError(e => { errs['errors'] = e?.error?.detail ?? 'Load failed'; return of(null); })
      ),
      cost: this.api.traceCost(range).pipe(
        catchError(e => { errs['cost'] = e?.error?.detail ?? 'Load failed'; return of(null); })
      ),
    }).subscribe(({ overview, tools, errors, cost }) => {
      this.overview.set(overview);
      this.tools.set(tools);
      this.errors.set(errors as TraceErrorsResponse | null);
      this.cost.set(cost);
      this.sectionErrors.set(errs);
      this.rebuildCharts(overview, tools, cost);
      this.loading.set(false);
    });
  }

  private rebuildCharts(
    overview: TraceOverview | null,
    tools: TraceToolsResponse | null,
    cost: TraceCostResponse | null,
  ) {
    // Tool horizontal bar (top 10 by call count)
    if (tools?.tools.length) {
      const top = [...tools.tools].sort((a, b) => b.call_count - a.call_count).slice(0, 10);
      this.toolBarData.set({
        labels: top.map(t => t.tool_name),
        datasets: [{
          data: top.map(t => t.call_count),
          label: 'Calls',
          backgroundColor: C_ACCENT,
          borderRadius: 3,
        }],
      });
    }

    // Mode pie
    if (overview?.mode_breakdown && Object.keys(overview.mode_breakdown).length) {
      const labels = Object.keys(overview.mode_breakdown);
      const palette = [C_ACCENT, C_INFO, C_SUCCESS, C_WARNING];
      this.modePieData.set({
        labels,
        datasets: [{
          data: labels.map(k => overview.mode_breakdown[k]),
          backgroundColor: palette.slice(0, labels.length),
          borderWidth: 2,
          borderColor: '#ffffff',
        }],
      });
    }

    // Cost line
    if (cost?.cost_by_day.length) {
      this.costLineData.set({
        labels: cost.cost_by_day.map(d => d.day),
        datasets: [{
          data: cost.cost_by_day.map(d => d.cost),
          label: 'Cost (USD)',
          fill: true,
          tension: 0.3,
          borderColor: C_ACCENT,
          backgroundColor: 'rgba(30, 41, 59, 0.07)',
          pointBackgroundColor: C_ACCENT,
          pointRadius: 3,
          pointHoverRadius: 5,
        }],
      });
    }
  }

  // ── Derived state ─────────────────────────────────────────────────────────

  successRateNum(): number {
    const ov = this.overview();
    if (!ov?.total_queries) return 0;
    return ((ov.status_breakdown['success'] ?? 0) / ov.total_queries) * 100;
  }

  successRate(): string {
    const n = this.successRateNum();
    return n === 0 && !this.overview()?.total_queries ? '—' : `${n.toFixed(1)}%`;
  }

  isSlowP95(): boolean {
    const p = this.overview()?.latency_ms.p95;
    return p !== null && p !== undefined && p > 30000;
  }

  isSlowP99(): boolean {
    const p = this.overview()?.latency_ms.p99;
    return p !== null && p !== undefined && p > 60000;
  }

  hasModeSplit(): boolean {
    const mb = this.overview()?.mode_breakdown;
    return !!mb && Object.values(mb).some(v => v > 0);
  }

  sortedTools() {
    return [...(this.tools()?.tools ?? [])].sort((a, b) => b.call_count - a.call_count);
  }

  hasErrors(): boolean {
    return Object.keys(this.sectionErrors()).length > 0;
  }

  errorEntries(): [string, string][] {
    return Object.entries(this.sectionErrors());
  }

  statusCount(status: string): number {
    return this.overview()?.status_breakdown[status] ?? 0;
  }

  // ── Navigation ────────────────────────────────────────────────────────────

  goToTrace(traceId: string) {
    this.router.navigate(['/traces', traceId]);
  }

  // ── Display helpers ───────────────────────────────────────────────────────

  formatDuration(ms: number | null | undefined): string {
    if (ms === null || ms === undefined) return '—';
    return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
  }

  formatCost(cost: number | null | undefined): string {
    if (cost === null || cost === undefined) return '—';
    return cost < 1 ? `$${cost.toFixed(4)}` : `$${cost.toFixed(2)}`;
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

  truncate(s: string | null, len = 80): string {
    if (!s) return '—';
    return s.length > len ? s.slice(0, len) + '…' : s;
  }
}
