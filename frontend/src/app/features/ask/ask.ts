import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import {
  ApiService,
  ChatMessage,
  ConversationSummary,
  QueryMode,
  QueryResponse,
  SourceInfo,
} from '../../core/api.service';
import { ConfidenceBadge } from '../../shared/confidence-badge/confidence-badge';
import { SourceDrawer } from '../../shared/source-drawer/source-drawer';
import { ApiKeyInput } from '../../shared/api-key-input/api-key-input';
import { ChatSidebar } from '../../shared/chat-sidebar/chat-sidebar';
import { FeedbackPanel } from '../ask/feedback-panel';
import { ModeSelector } from '../../shared/mode-selector/mode-selector';
import { AgentTranscript, AgentRequest } from './agent-transcript';

const PMS_SERVICES = [
  'VISITOR', 'MEETING_ROOMS', 'BOOKING-RULE-ENGINE', 'WIS-SEAT-BOOKING',
  'GUARD-APP', 'EMAIL-EMP-EXPERIENCE', 'EMP-EXP-INTERNAL-CONFIG',
  'EMP-EXP-COMMON-CONFIG', 'PROJECT-MANAGEMENT-SERVICE', 'APP_SERVER_CONFIG', 'ETS',
];

@Component({
  selector: 'app-ask',
  imports: [
    CommonModule, FormsModule, RouterLink,
    ConfidenceBadge, SourceDrawer, ApiKeyInput, FeedbackPanel,
    ModeSelector, AgentTranscript, ChatSidebar,
  ],
  template: `
    <div class="ask-shell">
      <!-- ── Sidebar: conversations ─────────────────────────────────── -->
      <app-chat-sidebar
        [conversations]="conversations()"
        [activeId]="conversationId()"
        [loading]="sidebarLoading()"
        (newChat)="onNewChat()"
        (openChat)="onOpenChat($event)"
        (deleteChat)="onDeleteChat($event)"
      />

      <!-- ── Chat column ─────────────────────────────────────────────── -->
      <div class="chat-column">
        <section class="conversation" aria-live="polite">
          <div class="conversation-inner">

            @if (showEmptyState()) {
              <div class="empty-state">
                <h1 class="empty-title">What can I help you find?</h1>
                <p class="empty-sub">
                  Ask about a WorkInSync feature, PMS config, Jira history, or live debug.
                </p>
              </div>
            }

            @for (m of messages(); track m.id) {
              @if (m.role === 'user') {
                <article class="message message-user">
                  <div class="message-meta">You</div>
                  <div class="message-bubble">{{ m.content }}</div>
                </article>
              } @else if (m.role === 'assistant') {
                <article class="message message-assistant">
                  <div class="message-meta">
                    Conwo
                    @if (m.mode) { <span class="meta-sub">· {{ modeLabel(m.mode) }}</span> }
                  </div>
                  <div class="message-body">
                    <div class="answer-header">
                      @if (m.confidence) {
                        <app-confidence-badge [confidence]="m.confidence" />
                      }
                      @if (m.mode === 'api' || m.mode === 'agent') {
                        <span class="pill pill-deep">
                          {{ m.mode === 'agent' ? 'Claude Code' : 'Deep Search' }}
                        </span>
                      }
                      @if (m.answer_id) {
                        <span class="answer-id" title="Answer ID">{{ m.answer_id }}</span>
                      }
                    </div>

                    @if (m.missing_context && m.missing_context.length > 0) {
                      <div class="notice notice-warning">
                        <strong>Missing context</strong> — answer may be incomplete:
                        <ul>
                          @for (item of m.missing_context; track item) {
                            <li>{{ item }}</li>
                          }
                        </ul>
                      </div>
                    }

                    <div class="answer-body" [innerHTML]="renderMarkdown(m.content)"></div>

                    @if (m.sources && hasSources(m.sources)) {
                      <app-source-drawer
                        [wikiPages]="m.sources.wiki_pages"
                        [jiraKeys]="m.sources.jira_keys"
                        [pmsConfigs]="m.sources.pms_configs"
                      />
                    }

                    @if (m.tool_trace && m.tool_trace.length > 0) {
                      <details class="trace-panel">
                        <summary>
                          <span class="trace-summary-text">Evidence gathering</span>
                          <span class="trace-count">{{ m.tool_trace.length }} step{{ m.tool_trace.length === 1 ? '' : 's' }}</span>
                        </summary>
                        <ol class="trace-timeline">
                          @for (entry of m.tool_trace; track $index) {
                            <li class="trace-step">
                              <div class="trace-step-head">
                                <span class="trace-round">R{{ entry.round || ($index + 1) }}</span>
                                <span class="trace-source" [class]="'src-' + sourceTypeFor(entry.tool_name)">
                                  {{ sourceLabelFor(entry.tool_name) }}
                                </span>
                                <span class="trace-tool">{{ entry.tool_name }}</span>
                                <span class="trace-status" [class.s-error]="isErrorOutput(entry.output_summary)">
                                  {{ isErrorOutput(entry.output_summary) ? 'error' : 'ok' }}
                                </span>
                              </div>
                              @if (entry.input) {
                                <div class="trace-input">
                                  <span class="trace-label">in</span>
                                  <code>{{ stringifyInput(entry.input) }}</code>
                                </div>
                              }
                              @if (entry.output_summary) {
                                <div class="trace-output">
                                  <span class="trace-label">out</span>
                                  <code>{{ entry.output_summary }}</code>
                                </div>
                              }
                            </li>
                          }
                        </ol>
                      </details>
                    }

                    @if (m.answer_id) {
                      <app-feedback-panel
                        [answerId]="m.answer_id"
                        [question]="questionBefore(m.id)"
                        [sources]="m.sources?.wiki_pages ?? []"
                      />
                    }
                  </div>
                </article>
              }
            }

            @if (loading()) {
              <article class="message message-assistant">
                <div class="message-meta">Conwo</div>
                <div class="message-body">
                  <div class="thinking">
                    <span class="thinking-dots" aria-hidden="true"><i></i><i></i><i></i></span>
                    <span class="thinking-text">Deep Search — gathering wiki, Jira, and PMS evidence…</span>
                  </div>
                </div>
              </article>
            }

            @if (agentActive()) {
              <article class="message message-assistant">
                <div class="message-meta">Conwo <span class="meta-sub">· Claude Code</span></div>
                <div class="message-body">
                  <app-agent-transcript
                    [request]="agentRequest()"
                    (completed)="onAgentCompleted($event)"
                  />
                </div>
              </article>
            }

            @if (error()) {
              <div class="notice notice-error" role="alert">{{ error() }}</div>
            }

            <div #endAnchor></div>
          </div>
        </section>

        <!-- ── Composer ─────────────────────────────────────────────── -->
        <footer class="composer-wrap">
          <div class="composer">

            @if (mode() === 'api' && !apiKey && !hasServerKey()) {
              <app-api-key-input (keyChanged)="onApiKeyChange($event)" />
            }

            @if (mode() === 'agent' && !claudeCodeAvailable()) {
              <div class="notice notice-warning">
                Claude Code CLI not found on the backend. Install it and run
                <code>claude login</code>, then refresh.
              </div>
            }

            <div class="scope-row">
              <label class="scope-chip">
                <span class="chip-label">Server</span>
                <select [(ngModel)]="server" [disabled]="loading()" class="chip-control">
                  <option value="com">.com</option>
                  <option value="in">.in</option>
                </select>
              </label>

              <label class="scope-chip">
                <span class="chip-label">BUID</span>
                <input
                  type="text"
                  [(ngModel)]="buid"
                  placeholder="optional"
                  class="chip-control chip-input"
                  [disabled]="loading()"
                />
              </label>

              <details class="scope-more">
                <summary>
                  Advanced scope
                  @if (advancedScopeCount() > 0) { <span class="chip-count">{{ advancedScopeCount() }}</span> }
                </summary>
                <div class="scope-grid">
                  <label class="scope-field">
                    <span>Service</span>
                    <select [(ngModel)]="service">
                      <option value="">any</option>
                      @for (svc of pmsServices; track svc) {
                        <option [value]="svc">{{ svc }}</option>
                      }
                    </select>
                  </label>
                  <label class="scope-field">
                    <span>OFFICEID</span>
                    <input type="text" [(ngModel)]="officeid" placeholder="LOpwcind-…" />
                  </label>
                  <label class="scope-field">
                    <span>ROOMID</span>
                    <input type="text" [(ngModel)]="roomid" placeholder="meeting-rooms only" />
                  </label>
                  <label class="scope-field">
                    <span>Role</span>
                    <input type="text" [(ngModel)]="role" placeholder="e.g. employee" />
                  </label>
                </div>
              </details>

              <a class="scope-link" routerLink="/search">Search without AI →</a>
            </div>

            <div class="composer-input-wrap" [class.disabled]="!canAsk()">
              <textarea
                [(ngModel)]="question"
                placeholder="Ask anything about WorkInSync…"
                class="composer-input"
                rows="1"
                (keydown)="onComposerKeydown($event)"
                [disabled]="loading() || agentActive()"
                aria-label="Ask a question"
              ></textarea>
              <button
                class="send-btn"
                type="button"
                (click)="ask()"
                [disabled]="loading() || agentActive() || !question.trim() || !canAsk()"
                [attr.aria-label]="loading() ? 'Working' : 'Send'"
                [title]="sendButtonTitle()"
              >
                @if (loading() || agentActive()) {
                  <span class="send-spinner" aria-hidden="true"></span>
                } @else {
                  <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
                    <path d="M8 1.5L8 14.5 M8 1.5L3 6.5 M8 1.5L13 6.5"
                          fill="none" stroke="currentColor" stroke-width="1.75"
                          stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                }
              </button>
            </div>

            <div class="composer-bottom">
              <app-mode-selector
                [currentMode]="mode()"
                [claudeCodeAvailable]="claudeCodeAvailable()"
                [localDev]="claudeCodeLocalDev()"
                (modeChanged)="onModeChange($event)"
              />
              @if (mode() === 'api' && apiKey) {
                <span class="key-indicator" title="API key configured">
                  <span class="key-dot"></span>
                  Key set ·••••{{ apiKey.slice(-4) }}
                  <button class="link-btn" (click)="clearApiKey()" type="button">change</button>
                </span>
              }
            </div>
          </div>
        </footer>
      </div>
    </div>
  `,
  styleUrl: './ask.scss'
})
export class Ask implements OnInit {
  private api = inject(ApiService);

  question = '';
  server: 'com' | 'in' = 'com';
  buid = '';
  service = '';
  officeid = '';
  roomid = '';
  role = '';
  apiKey = '';

  readonly pmsServices = PMS_SERVICES;

  mode = signal<QueryMode>('api');
  claudeCodeAvailable = signal(false);
  claudeCodeLocalDev = signal(false);
  claudeCodeNote = signal('');
  hasServerKey = signal(false);
  loading = signal(false);
  agentActive = signal(false);
  error = signal('');

  messages = signal<ChatMessage[]>([]);
  conversationId = signal<string | null>(null);
  conversations = signal<ConversationSummary[]>([]);
  sidebarLoading = signal(false);
  agentRequest = signal<AgentRequest | null>(null);

  ngOnInit() {
    const stored = this.api.getStoredMode();
    // Migrate any user previously on the legacy single-shot mode to Deep Search.
    this.mode.set(stored === 'claude-code' ? 'api' : stored);
    this.apiKey = this.api.getStoredApiKey();
    this.api.checkClaudeCodeHealth().subscribe({
      next: r => {
        this.claudeCodeAvailable.set(r.available);
        this.claudeCodeLocalDev.set(!!r.local_dev_unauthenticated);
        this.claudeCodeNote.set(r.note ?? '');
      },
      error: () => {
        this.claudeCodeAvailable.set(false);
        this.claudeCodeLocalDev.set(false);
        this.claudeCodeNote.set('');
      },
    });
    this.api.health().subscribe({
      next: h => this.hasServerKey.set(h.has_server_key ?? false),
      error: () => {},
    });
    this.refreshConversations();
  }

  // ── Sidebar ──────────────────────────────────────────────────────────

  refreshConversations() {
    this.sidebarLoading.set(true);
    this.api.listConversations().subscribe({
      next: r => {
        this.conversations.set(r.conversations);
        this.sidebarLoading.set(false);
      },
      error: () => this.sidebarLoading.set(false),
    });
  }

  onNewChat() {
    this.conversationId.set(null);
    this.messages.set([]);
    this.error.set('');
    this.question = '';
  }

  onOpenChat(id: string) {
    if (id === this.conversationId()) return;
    this.error.set('');
    this.api.getConversation(id).subscribe({
      next: c => {
        this.conversationId.set(c.id);
        this.messages.set(c.messages);
      },
      error: () => this.error.set('Could not load conversation.'),
    });
  }

  onDeleteChat(id: string) {
    this.api.deleteConversation(id).subscribe({
      next: () => {
        if (this.conversationId() === id) {
          this.onNewChat();
        }
        this.refreshConversations();
      },
      error: () => this.error.set('Failed to delete conversation.'),
    });
  }

  // ── Mode + key ───────────────────────────────────────────────────────

  onModeChange(m: QueryMode) {
    this.mode.set(m);
    this.api.setMode(m);
    this.error.set('');
  }

  onApiKeyChange(key: string) {
    this.apiKey = key;
  }

  clearApiKey() {
    this.apiKey = '';
    this.api.setApiKey('');
  }

  hasAdminToken(): boolean {
    return !!this.api.getAdminToken();
  }

  canAsk(): boolean {
    if (this.mode() === 'api') return !!this.apiKey || this.hasServerKey();
    if (this.mode() === 'agent') {
      if (!this.claudeCodeAvailable()) return false;
      return this.claudeCodeLocalDev() || this.hasAdminToken();
    }
    return false;
  }

  showEmptyState(): boolean {
    return this.messages().length === 0 && !this.loading() && !this.agentActive();
  }

  advancedScopeCount(): number {
    return [this.service, this.officeid, this.roomid, this.role].filter(Boolean).length;
  }

  onComposerKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      this.ask();
    }
  }

  // ── Ask flow ─────────────────────────────────────────────────────────

  ask() {
    const q = this.question.trim();
    if (!q || !this.canAsk()) return;

    if (this.mode() === 'api' && !this.apiKey && !this.hasServerKey()) {
      this.error.set('Add your Anthropic API key in the composer to use Deep Search.');
      return;
    }
    if (this.mode() === 'agent' && !this.hasAdminToken() && !this.claudeCodeLocalDev()) {
      this.error.set(
        'Claude Code mode needs either CONWO_LOCAL_CLAUDE_CODE=true on the backend ' +
        '(local-dev), or an admin Bearer token from the Admin section.'
      );
      return;
    }

    this.error.set('');
    this.question = '';

    // Optimistically render the user message so the UI feels instant.
    const optimisticUser: ChatMessage = {
      id: `local-${Date.now()}`,
      conversation_id: this.conversationId() ?? '',
      role: 'user',
      content: q,
      created_at: new Date().toISOString(),
      mode: this.mode(),
      server: this.server,
      buid: this.buid || undefined,
    };
    this.messages.update(arr => [...arr, optimisticUser]);

    if (this.mode() === 'agent') {
      this.runAgent(q);
      return;
    }

    this.runDeepSearch(q);
  }

  private runDeepSearch(q: string) {
    this.loading.set(true);

    const payload = {
      question: q,
      mode: 'api' as QueryMode,
      claude_api_key: this.apiKey,
      server: this.server,
      buid: this.buid || undefined,
      service: this.service || undefined,
      officeid: this.officeid || undefined,
      roomid: this.roomid || undefined,
      role: this.role || undefined,
      conversation_id: this.conversationId() ?? undefined,
    };

    this.api.query(payload).subscribe({
      next: res => {
        this.loading.set(false);
        if (res.error) {
          this.error.set(res.error);
          return;
        }
        if (res.conversation_id) this.conversationId.set(res.conversation_id);
        this.appendAssistantFromResponse(res);
        this.refreshConversations();
      },
      error: err => {
        this.loading.set(false);
        this.error.set(err?.error?.detail ?? 'Request failed. Is the backend running on localhost:8000?');
      },
    });
  }

  private runAgent(q: string) {
    // Build the request first; setting agentActive renders the transcript,
    // and its `effect()` picks up the request on first read — no ViewChild
    // timing race.
    this.agentRequest.set({
      question: q,
      conversationId: this.conversationId() ?? undefined,
      server: this.server,
      buid: this.buid || undefined,
    });
    this.agentActive.set(true);
  }

  onAgentCompleted(event: { conversationId: string; success: boolean }) {
    this.agentActive.set(false);
    this.agentRequest.set(null);
    if (event.conversationId) {
      this.conversationId.set(event.conversationId);
      // Reload the conversation so the static rendering replaces the live transcript.
      this.api.getConversation(event.conversationId).subscribe({
        next: c => this.messages.set(c.messages),
      });
    }
    this.refreshConversations();
  }

  private appendAssistantFromResponse(res: QueryResponse) {
    const msg: ChatMessage = {
      id: `local-${Date.now()}`,
      conversation_id: res.conversation_id ?? '',
      role: 'assistant',
      content: res.answer_text,
      created_at: new Date().toISOString(),
      mode: res.mode,
      confidence: res.confidence,
      answer_id: res.answer_id,
      sources: res.sources,
      tool_trace: res.tool_trace,
      missing_context: res.missing_context,
    };
    this.messages.update(arr => [...arr, msg]);
  }

  // ── Template helpers ─────────────────────────────────────────────────

  sendButtonTitle(): string {
    if (this.loading() || this.agentActive()) return 'Working…';
    if (!this.question.trim()) return 'Type a question first';
    if (this.mode() === 'api' && !this.apiKey && !this.hasServerKey()) {
      return 'Add your Anthropic API key in the composer to use Deep Search.';
    }
    if (this.mode() === 'agent') {
      if (!this.claudeCodeAvailable()) {
        return 'Claude Code CLI is not installed on the backend machine.';
      }
      if (!this.claudeCodeLocalDev() && !this.hasAdminToken()) {
        return 'Sign in via Admin, or start the backend with CONWO_LOCAL_CLAUDE_CODE=true for local-dev.';
      }
    }
    return 'Send';
  }

  modeLabel(m: string): string {
    if (m === 'api') return 'Deep Search';
    if (m === 'agent' || m === 'claude-code-agent') return 'Claude Code';
    if (m === 'claude-code') return 'Claude Code';
    return m;
  }

  hasSources(s: SourceInfo | null | undefined): boolean {
    if (!s) return false;
    return (s.wiki_pages?.length ?? 0) + (s.jira_keys?.length ?? 0) + (s.pms_configs?.length ?? 0) > 0;
  }

  questionBefore(assistantId: string): string {
    const all = this.messages();
    const idx = all.findIndex(m => m.id === assistantId);
    for (let i = idx - 1; i >= 0; i--) {
      if (all[i].role === 'user') return all[i].content;
    }
    return '';
  }

  sourceTypeFor(toolName: string): string {
    if (toolName.startsWith('wiki_')) return 'wiki';
    if (toolName.startsWith('jira_')) return 'jira';
    if (toolName.startsWith('pms_')) return 'pms';
    if (toolName.startsWith('config_')) return 'config';
    if (toolName.startsWith('feedback')) return 'feedback';
    return 'other';
  }

  sourceLabelFor(toolName: string): string {
    return this.sourceTypeFor(toolName).toUpperCase();
  }

  stringifyInput(input: unknown): string {
    try {
      const s = JSON.stringify(input);
      return s.length > 240 ? s.slice(0, 237) + '…' : s;
    } catch {
      return String(input);
    }
  }

  isErrorOutput(out: string | undefined): boolean {
    if (!out) return false;
    return /"error"|"code"\s*:\s*"(?:tool_exception|unknown_tool|api_error)"/i.test(out);
  }

  renderMarkdown(md: string | null | undefined): string {
    if (!md) return '';
    return md
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^# (.+)$/gm, '<h1>$1</h1>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
      .replace(/\n\n+/g, '</p><p>')
      .replace(/^(?!<[hul])/gm, '')
      .replace(/^(.+)$/gm, (line) =>
        line.startsWith('<') ? line : `<p>${line}</p>`
      );
  }
}
