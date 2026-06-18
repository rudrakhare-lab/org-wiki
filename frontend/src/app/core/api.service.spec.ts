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
