import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, SearchResponse } from '../../core/api.service';

const JIRA_BASE = 'https://moveinsync.atlassian.net/browse/';

@Component({
  selector: 'app-search',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="search-page">
      <header class="search-header">
        <h1>🔍 Search</h1>
        <p>Raw wiki + Jira search — no AI, no API key needed.</p>
      </header>

      <div class="search-bar">
        <input
          type="text"
          [(ngModel)]="query"
          placeholder="Search wiki pages and Jira tickets…"
          class="search-input"
          (keydown.enter)="search()"
          [disabled]="loading()"
        />
        <select [(ngModel)]="server" class="server-select">
          <option value="com">.com</option>
          <option value="in">.in</option>
        </select>
        <button class="search-btn" (click)="search()" [disabled]="loading() || !query.trim()">
          {{ loading() ? 'Searching…' : 'Search' }}
        </button>
      </div>

      @if (results()) {
        <div class="results">

          @if (results()!.wiki_pages.length) {
            <section class="result-section">
              <h3>Wiki pages</h3>
              @for (page of results()!.wiki_pages; track page.path) {
                <div class="result-item">
                  <div class="result-title">📄 {{ page.title }}</div>
                  <div class="result-path">{{ page.path }}</div>
                  <div class="result-excerpt">{{ page.excerpt }}</div>
                </div>
              }
            </section>
          }

          <section class="result-section">
            <h3>Jira evidence
              <span class="bucket-summary">
                Latest: {{ results()!.jira_buckets.LATEST.length }} ·
                Historical: {{ results()!.jira_buckets.HISTORICAL.length }}
              </span>
            </h3>

            @if (results()!.jira_buckets.LATEST.length) {
              <div class="bucket-label latest">Latest (last 6 months)</div>
              @for (t of results()!.jira_buckets.LATEST; track t.key) {
                <div class="ticket-item">
                  <a [href]="jiraBase + t.key" target="_blank" class="ticket-key">{{ t.key }}</a>
                  <span class="ticket-status" [class]="'status-' + t.status">{{ t.status }}</span>
                  @if (t.hit_summary) { <span class="hit-badge">title match</span> }
                  <span class="ticket-date">updated {{ t.updated }}</span>
                  <div class="ticket-summary">{{ t.summary }}</div>
                </div>
              }
            }

            @if (results()!.jira_buckets.HISTORICAL.length) {
              <div class="bucket-label historical">Historical</div>
              @for (t of results()!.jira_buckets.HISTORICAL.slice(0, 8); track t.key) {
                <div class="ticket-item historical">
                  <a [href]="jiraBase + t.key" target="_blank" class="ticket-key">{{ t.key }}</a>
                  <span class="ticket-status">{{ t.status }}</span>
                  <span class="ticket-date">updated {{ t.updated }}</span>
                  <div class="ticket-summary">{{ t.summary }}</div>
                </div>
              }
            }

            @if (!results()!.jira_buckets.LATEST.length && !results()!.jira_buckets.HISTORICAL.length) {
              <div class="empty-state">No Jira tickets matched "{{ query }}"</div>
            }
          </section>

        </div>
      }
    </div>
  `,
  styles: [`
    .search-page { max-width: 860px; margin: 0 auto; padding: 32px 16px; }
    .search-header h1 { font-size: 1.5rem; margin: 0 0 4px; color: #1e1b4b; }
    .search-header p { color: #6b7280; margin: 0 0 20px; font-size: 0.875rem; }
    .search-bar { display: flex; gap: 10px; margin-bottom: 24px; }
    .search-input {
      flex: 1; padding: 10px 14px; border: 1px solid #d1d5db;
      border-radius: 8px; font-size: 0.95rem;
      &:focus { outline: none; border-color: #6366f1; }
      &:disabled { background: #f9fafb; }
    }
    .server-select {
      padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;
      background: white; font-size: 0.875rem;
    }
    .search-btn {
      background: #4f46e5; color: white; border: none; border-radius: 8px;
      padding: 10px 20px; cursor: pointer; font-weight: 600;
      &:disabled { background: #c7d2fe; cursor: not-allowed; }
    }
    .result-section { margin-bottom: 28px; }
    .result-section h3 {
      font-size: 0.9rem; font-weight: 600; color: #374151; margin: 0 0 12px;
      display: flex; align-items: center; gap: 10px;
    }
    .bucket-summary { font-size: 0.75rem; font-weight: 400; color: #9ca3af; }
    .result-item {
      border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px;
      margin-bottom: 8px; background: white;
    }
    .result-title { font-weight: 600; color: #1f2937; margin-bottom: 2px; }
    .result-path { font-size: 0.75rem; color: #6366f1; font-family: monospace; margin-bottom: 6px; }
    .result-excerpt { font-size: 0.85rem; color: #4b5563; line-height: 1.5; }
    .bucket-label {
      font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
      padding: 4px 10px; border-radius: 4px; display: inline-block; margin-bottom: 8px;
      &.latest { background: #d1fae5; color: #065f46; }
      &.historical { background: #f3f4f6; color: #6b7280; }
    }
    .ticket-item {
      padding: 10px 0; border-bottom: 1px solid #f3f4f6;
      display: flex; flex-wrap: wrap; gap: 8px; align-items: baseline;
      &.historical { opacity: 0.8; }
    }
    .ticket-key {
      color: #4f46e5; font-weight: 700; font-family: monospace; font-size: 0.875rem;
      text-decoration: none;
      &:hover { text-decoration: underline; }
    }
    .ticket-status {
      font-size: 0.7rem; padding: 1px 7px; border-radius: 10px;
      background: #f3f4f6; color: #374151;
      &.status-done { background: #d1fae5; color: #065f46; }
      &.status-new, &.status-indeterminate { background: #eff6ff; color: #1d4ed8; }
    }
    .hit-badge {
      font-size: 0.7rem; background: #fef3c7; color: #92400e;
      padding: 1px 7px; border-radius: 10px;
    }
    .ticket-date { font-size: 0.75rem; color: #9ca3af; }
    .ticket-summary { width: 100%; font-size: 0.875rem; color: #4b5563; }
    .empty-state { color: #9ca3af; font-size: 0.875rem; padding: 16px 0; }
  `]
})
export class Search {
  private api = inject(ApiService);

  query = '';
  server: 'com' | 'in' = 'com';
  loading = signal(false);
  results = signal<SearchResponse | null>(null);
  jiraBase = JIRA_BASE;

  search() {
    if (!this.query.trim()) return;
    this.loading.set(true);
    this.api.search(this.query, this.server).subscribe({
      next: res => {
        this.loading.set(false);
        this.results.set(res);
      },
      error: () => this.loading.set(false),
    });
  }
}
