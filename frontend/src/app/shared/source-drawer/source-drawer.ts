import { Component, input, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, WikiPage } from '../../core/api.service';

const JIRA_BASE = 'https://moveinsync.atlassian.net/browse/';

@Component({
  selector: 'app-source-drawer',
  imports: [CommonModule],
  template: `
    @if (totalCount() > 0) {
      <details class="source-drawer" (toggle)="onToggle($event)">
        <summary>
          Sources
          <span class="count">{{ totalCount() }}</span>
        </summary>

        <div class="drawer-body">
          @if (wikiPages().length) {
            <section>
              <h4>Wiki</h4>
              <ul class="source-list">
                @for (path of wikiPages(); track path) {
                  <li>
                    <button class="source-link" (click)="loadWikiPage(path)" type="button">
                      {{ path }}
                    </button>
                  </li>
                }
              </ul>
              @if (previewPage()) {
                <div class="wiki-preview">
                  <div class="preview-header">
                    <strong>{{ previewPage()!.title }}</strong>
                    <button class="close-btn" (click)="previewPage.set(null)" aria-label="Close preview" type="button">×</button>
                  </div>
                  <pre class="preview-body">{{ previewPage()!.content.slice(0, 1500) }}{{ previewPage()!.content.length > 1500 ? '\n…' : '' }}</pre>
                </div>
              }
            </section>
          }

          @if (jiraKeys().length) {
            <section>
              <h4>Jira</h4>
              <ul class="source-list">
                @for (key of jiraKeys(); track key) {
                  <li>
                    <a [href]="jiraBase + key" target="_blank" rel="noopener" class="source-link">{{ key }}</a>
                  </li>
                }
              </ul>
            </section>
          }

          @if (pmsConfigs().length) {
            <section>
              <h4>PMS configs</h4>
              <ul class="source-list">
                @for (cfg of pmsConfigs(); track cfg) {
                  <li><code>{{ cfg }}</code></li>
                }
              </ul>
            </section>
          }
        </div>
      </details>
    }
  `,
  styles: [`
    .source-drawer {
      border-top: 1px solid var(--border);
      padding-top: 12px;
    }

    summary {
      cursor: pointer;
      user-select: none;
      list-style: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 0.78rem;
      font-weight: 500;
      color: var(--text-muted);

      &::before {
        content: '›';
        display: inline-block;
        transition: transform 0.15s;
        color: var(--text-subtle);
        font-size: 0.9rem;
      }
    }
    .source-drawer[open] summary::before { transform: rotate(90deg); }

    .count {
      background: var(--surface-muted);
      border: 1px solid var(--border);
      color: var(--text-muted);
      border-radius: var(--radius-pill);
      padding: 0 8px;
      font-size: 0.7rem;
      font-weight: 600;
    }

    .drawer-body {
      margin-top: 14px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    section { display: flex; flex-direction: column; gap: 4px; }
    h4 {
      margin: 0;
      font-size: 0.66rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-subtle);
    }

    .source-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .source-list li {
      font-size: 0.85rem;
      color: var(--text-muted);
      font-family: var(--font-mono);
    }

    .source-link {
      background: none;
      border: none;
      color: var(--accent);
      cursor: pointer;
      padding: 1px 0;
      font: inherit;
      text-align: left;
      text-decoration: none;

      &:hover { text-decoration: underline; }
    }

    code {
      background: var(--surface-muted);
      border: 1px solid var(--border);
      padding: 1px 6px;
      border-radius: var(--radius-xs);
      font-size: 0.78rem;
    }

    .wiki-preview {
      margin-top: 8px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
      background: var(--surface-inset);
    }
    .preview-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      background: var(--surface-muted);
      border-bottom: 1px solid var(--border);
      font-size: 0.85rem;
    }
    .close-btn {
      background: none;
      border: none;
      cursor: pointer;
      color: var(--text-muted);
      font-size: 1.05rem;
      line-height: 1;
      padding: 0 4px;
      &:hover { color: var(--text); }
    }
    .preview-body {
      margin: 0;
      padding: 12px;
      font-size: 0.78rem;
      font-family: var(--font-mono);
      overflow-x: auto;
      white-space: pre-wrap;
      max-height: 320px;
      overflow-y: auto;
      color: var(--text-muted);
    }
  `]
})
export class SourceDrawer {
  wikiPages = input<string[]>([]);
  jiraKeys = input<string[]>([]);
  pmsConfigs = input<string[]>([]);

  previewPage = signal<WikiPage | null>(null);
  jiraBase = JIRA_BASE;

  private api = inject(ApiService);

  totalCount() {
    return this.wikiPages().length + this.jiraKeys().length + this.pmsConfigs().length;
  }

  onToggle(_event: Event) {
    // Native <details> handles state; this is a hook if we ever want analytics.
  }

  loadWikiPage(path: string) {
    this.api.getWikiPage(path).subscribe({
      next: page => this.previewPage.set(page),
      error: () => this.previewPage.set(null),
    });
  }
}
