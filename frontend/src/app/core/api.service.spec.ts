import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ApiService } from './api.service';

describe('ApiService agent admin', () => {
  let api: ApiService; let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [ApiService, provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(ApiService); http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('POSTs name to /admin/agents', () => {
    api.createAgent('Legal').subscribe();
    const r = http.expectOne('/admin/agents');
    expect(r.request.method).toBe('POST');
    expect(r.request.body).toEqual({ name: 'Legal', description: '' });
    r.flush({ id: 'legal' });
  });

  it('PATCHes identity to /admin/agents/:id', () => {
    api.updateAgent('legal', { identity: 'x' }).subscribe();
    const r = http.expectOne('/admin/agents/legal');
    expect(r.request.method).toBe('PATCH');
    r.flush({ id: 'legal' });
  });

  it('DELETEs /admin/agents/:id', () => {
    api.archiveAgent('legal').subscribe();
    const r = http.expectOne('/admin/agents/legal');
    expect(r.request.method).toBe('DELETE');
    r.flush({ status: 'archived', id: 'legal' });
  });

  it('createAgent sends name + description', () => {
    api.createAgent('Legal', 'does legal').subscribe();
    const r = http.expectOne('/admin/agents');
    expect(r.request.body).toEqual({ name: 'Legal', description: 'does legal' });
    r.flush({ id: 'legal' });
  });

  it('deleteAgent hits hard=true', () => {
    api.deleteAgent('legal').subscribe();
    const r = http.expectOne('/admin/agents/legal?hard=true');
    expect(r.request.method).toBe('DELETE');
    r.flush({ status: 'deleted', id: 'legal' });
  });
});

describe('ApiService dashboard overview', () => {
  let api: ApiService; let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [ApiService, provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(ApiService); http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('GETs dashboard summary with time_range and agent_id', () => {
    api.dashboardSummary('7d', 'conwo').subscribe();
    const r = http.expectOne('/api/traces/dashboard/summary?time_range=7d&agent_id=conwo');
    expect(r.request.method).toBe('GET');
    r.flush({
      conversations: 2, queries: 3, msgs_per_conversation: 1.5,
      quality: { avg_score: 88, judged_count: 1 },
      escalation: { rate: 0.5, feedback_count: 1 },
      latency_ms: { avg: 1000, p95: 2000 },
      total_cost_usd: 0.05,
    });
  });

  it('GETs dashboard daily volume with time_range and agent_id', () => {
    api.dashboardDailyVolume('30d', 'all').subscribe();
    const r = http.expectOne('/api/traces/dashboard/daily-volume?time_range=30d&agent_id=all');
    expect(r.request.method).toBe('GET');
    r.flush({ days: [{ day: '2026-07-01', queries: 3, conversations: 2 }] });
  });

  it('defaults time_range and agent_id when omitted', () => {
    api.dashboardSummary().subscribe();
    http.expectOne('/api/traces/dashboard/summary?time_range=7d&agent_id=conwo');
  });
});
