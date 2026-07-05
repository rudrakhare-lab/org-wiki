import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs';
import { BaseChartDirective } from 'ng2-charts';
import type { ChartConfiguration, ChartData } from 'chart.js';
import { AgentService } from '../../core/agent.service';
import {
  ApiService,
  TraceOverview,
  TraceToolsResponse,
  TraceErrorsResponse,
  TraceCostResponse,
  DashboardSummary,
  DashboardDailyVolume,
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

type TabId = 'overview' | 'tools' | 'conversations' | 'cost' | 'quality' | 'review' | 'failures';

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'tools', label: 'Tool Performance' },
  { id: 'conversations', label: 'Conversations' },
  { id: 'cost', label: 'Tokens & Cost' },
  { id: 'quality', label: 'Quality' },
  { id: 'review', label: 'Review Queue' },
  { id: 'failures', label: 'Failure Analysis' },
];

@Component({
  selector: 'app-trace-dashboard',
  imports: [CommonModule, BaseChartDirective],
  template: `
    <div class="dashboard-shell">
      <nav class="dash-nav">
        @for (t of tabs; track t.id) {
          <button
            class="dash-nav-item"
            [class.active]="activeTab() === t.id"
            (click)="setTab(t.id)"
          >{{ t.label }}</button>
        }
      </nav>

      <div class="dash-main">
        <header class="page-header">
          <h1>Observability Dashboard</h1>
          <div class="header-actions">
            <select class="agent-select" [value]="agentFilter()" (change)="setAgentFilter($any($event.target).value)">
              <option value="all">All Agents</option>
              @for (a of agentSvc.agents(); track a.id) {
                <option [value]="a.id">{{ a.display_name }}</option>
              }
            </select>
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
          @if (hasErrors()) {
            <div class="section-errors">
              @for (e of errorEntries(); track e[0]) {
                <span class="section-error-badge">{{ e[0] }}: {{ e[1] }}</span>
              }
            </div>
          }

          @switch (activeTab()) {
            @case ('overview') {
              @if (summary()) {
                <div class="metric-cards">
                  <div class="metric-card">
                    <div class="metric-label">Conversations</div>
                    <div class="metric-value">{{ summary()!.conversations | number }}</div>
                    <div class="metric-sub">in {{ timeRange() }}</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-label">Queries</div>
                    <div class="metric-value">{{ summary()!.queries | number }}</div>
                    <div class="metric-sub">{{ summary()!.msgs_per_conversation ?? '—' }} msgs/conversation</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-label">Avg Quality Score</div>
                    <div class="metric-value">{{ formatScore(summary()!.quality.avg_score) }}</div>
                    <div class="metric-sub">{{ summary()!.quality.judged_count }} judged</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-label">Escalation Rate</div>
                    <div class="metric-value">{{ formatRate(summary()!.escalation.rate) }}</div>
                    <div class="metric-sub">{{ summary()!.escalation.feedback_count }} feedback received</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-label">Avg Latency</div>
                    <div class="metric-value">{{ formatDuration(summary()!.latency_ms.avg) }}</div>
                    <div class="metric-sub">p95 {{ formatDuration(summary()!.latency_ms.p95) }}</div>
                  </div>
                  <div class="metric-card">
                    <div class="metric-label">Est. Cost</div>
                    <div class="metric-value mono">{{ formatCost(summary()!.total_cost_usd) }}</div>
                    <div class="metric-sub">claude-code billed externally</div>
                  </div>
                </div>
              }

              <section class="section chart-card">
                <h2 class="section-heading">Daily Volume</h2>
                @if (dailyVolume() && dailyVolume()!.days.length > 0) {
                  <div class="chart-canvas-wrap">
                    <canvas baseChart
                      [type]="'line'"
                      [data]="dailyVolumeChartData()"
                      [options]="dailyVolumeOptions"
                    ></canvas>
                  </div>
                } @else {
                  <p class="empty-text">No query data for this period.</p>
                }
              </section>
            }
            @default {
              <div class="coming-soon">This tab is coming soon.</div>
            }
          }
        }
      </div>
    </div>
  `,
  styleUrl: './dashboard.scss',
})
export class Dashboard implements OnInit {
  private api = inject(ApiService);
  private router = inject(Router);
  agentSvc = inject(AgentService);

  readonly ranges = RANGES;
  readonly tabs = TABS;

  // State
  loading = signal(true);
  timeRange = signal('7d');
  overview = signal<TraceOverview | null>(null);
  tools = signal<TraceToolsResponse | null>(null);
  errors = signal<TraceErrorsResponse | null>(null);
  cost = signal<TraceCostResponse | null>(null);
  sectionErrors = signal<Record<string, string>>({});

  activeTab = signal<TabId>('overview');
  agentFilter = signal<string>('all');

  summary = signal<DashboardSummary | null>(null);
  dailyVolume = signal<DashboardDailyVolume | null>(null);

  // Chart data signals — new object references force ng2-charts ngOnChanges
  toolBarData = signal<ChartData<'bar'>>({ datasets: [] });
  modePieData = signal<ChartData<'pie'>>({ datasets: [] });
  costLineData = signal<ChartData<'line'>>({ datasets: [] });
  dailyVolumeChartData = signal<ChartData<'line'>>({ datasets: [] });

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

  readonly dailyVolumeOptions: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' } },
    scales: {
      y: { beginAtZero: true, grid: { color: C_BORDER }, ticks: { color: C_MUTED } },
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

  setTab(id: TabId): void {
    this.activeTab.set(id);
  }

  setAgentFilter(id: string): void {
    this.agentFilter.set(id);
    this.loadAll();
  }

  loadAll() {
    this.loading.set(true);
    const errs: Record<string, string> = {};
    const range = this.timeRange();
    const agentId = this.agentFilter();

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
      summary: this.api.dashboardSummary(range, agentId).pipe(
        catchError(e => { errs['summary'] = e?.error?.detail ?? 'Load failed'; return of(null); })
      ),
      dailyVolume: this.api.dashboardDailyVolume(range, agentId).pipe(
        catchError(e => { errs['dailyVolume'] = e?.error?.detail ?? 'Load failed'; return of(null); })
      ),
    }).subscribe(({ overview, tools, errors, cost, summary, dailyVolume }) => {
      this.overview.set(overview);
      this.tools.set(tools);
      this.errors.set(errors as TraceErrorsResponse | null);
      this.cost.set(cost);
      this.summary.set(summary);
      this.dailyVolume.set(dailyVolume);
      this.sectionErrors.set(errs);
      this.rebuildCharts(overview, tools, cost);
      this.rebuildDailyVolumeChart(dailyVolume);
      this.loading.set(false);
    });
  }

  private rebuildDailyVolumeChart(dv: DashboardDailyVolume | null): void {
    if (!dv?.days.length) return;
    this.dailyVolumeChartData.set({
      labels: dv.days.map(d => d.day),
      datasets: [
        { data: dv.days.map(d => d.queries), label: 'Queries', borderColor: C_ACCENT, backgroundColor: 'transparent', tension: 0.3 },
        { data: dv.days.map(d => d.conversations), label: 'Conversations', borderColor: C_INFO, backgroundColor: 'transparent', tension: 0.3 },
      ],
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

  formatScore(score: number | null | undefined): string {
    return score === null || score === undefined ? '—' : score.toFixed(1);
  }

  formatRate(rate: number | null | undefined): string {
    return rate === null || rate === undefined ? '—' : `${(rate * 100).toFixed(1)}%`;
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
