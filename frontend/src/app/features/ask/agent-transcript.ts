/**
 * Live transcript of a Claude Code agent session.
 *
 * Owns its own subscription to ApiService.streamQuery(). Renders each event as
 * an item: init banner, text block, tool-call card (collapsible), result, error.
 * Tool results are stitched onto their parent tool_use by tool_use_id.
 *
 * Parent calls start(question) to begin a new stream and stop() to cancel.
 */
import {
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
  effect,
  inject,
  input,
  output,
  signal,
  untracked,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { ApiService, AgentEvent, ContentBlock } from '../../core/api.service';
import { FeedbackPanel } from './feedback-panel';

export interface AgentRequest {
  question: string;
  conversationId?: string;
  server?: 'com' | 'in';
  buid?: string;
}

type ToolItem = {
  kind: 'tool';
  id: string;
  name: string;
  input: Record<string, unknown>;
  result?: string;
  isError?: boolean;
  pending: boolean;
  expanded: boolean;
};

type TranscriptItem =
  | {
      kind: 'init';
      cwd?: string;
      toolCount?: number;
      mcpCount?: number;
      model?: string;
    }
  | { kind: 'text'; text: string }
  | { kind: 'thinking'; text: string }
  | ToolItem
  | {
      kind: 'result';
      text: string;
      cost?: number;
      turns?: number;
      durationMs?: number;
      isError?: boolean;
    }
  | { kind: 'error'; text: string };

type Status = 'idle' | 'streaming' | 'done' | 'error';

@Component({
  selector: 'app-agent-transcript',
  imports: [CommonModule, FeedbackPanel],
  template: `
    <div class="transcript">
      <div class="transcript-header">
        <span class="status-badge" [class]="'status-' + status()">
          @switch (status()) {
            @case ('streaming') {
              <span class="spinner-small"></span>
              <span>Streaming…</span>
            }
            @case ('done') { <span>✓ Complete</span> }
            @case ('error') { <span>⚠ Error</span> }
            @default { <span>Ready</span> }
          }
        </span>
        @if (status() === 'streaming') {
          <button class="stop-btn" (click)="stop()">⏹ Stop</button>
        }
      </div>

      @if (error()) {
        <div class="transcript-error">{{ error() }}</div>
      }

      @for (item of items(); track $index) {
        @switch (item.kind) {
          @case ('init') {
            <div class="item item-init">
              <span class="init-label">session</span>
              <span>cwd: <code>{{ item.cwd }}</code></span>
              @if (item.toolCount !== undefined) {
                <span>· {{ item.toolCount }} tools</span>
              }
              @if (item.mcpCount !== undefined) {
                <span>· {{ item.mcpCount }} mcp</span>
              }
              @if (item.model) {
                <span>· {{ item.model }}</span>
              }
            </div>
          }
          @case ('text') {
            <div class="item item-text" [innerHTML]="renderMarkdown(item.text)"></div>
          }
          @case ('thinking') {
            <details class="item item-thinking">
              <summary>thinking</summary>
              <pre>{{ item.text }}</pre>
            </details>
          }
          @case ('tool') {
            <div class="item item-tool" [class.tool-error]="item.isError">
              <div class="tool-header" (click)="toggleTool(item.id)">
                <span class="tool-marker" aria-hidden="true"></span>
                <span class="tool-name">{{ item.name }}</span>
                <span class="tool-input-summary">{{ toolInputSummary(item) }}</span>
                @if (item.pending) {
                  <span class="spinner-small" aria-label="Running"></span>
                } @else if (item.isError) {
                  <span class="badge-error">error</span>
                } @else {
                  <span class="badge-done">done</span>
                }
                <span class="expand-caret" aria-hidden="true">{{ item.expanded ? '▾' : '▸' }}</span>
              </div>
              @if (item.expanded) {
                <div class="tool-details">
                  <div class="tool-section">
                    <span class="tool-label">input</span>
                    <pre>{{ formatJson(item.input) }}</pre>
                  </div>
                  @if (item.result !== undefined) {
                    <div class="tool-section">
                      <span class="tool-label">result</span>
                      <pre>{{ item.result }}</pre>
                    </div>
                  }
                </div>
              }
            </div>
          }
          @case ('result') {
            <div class="item item-result" [class.result-error]="item.isError">
              <div class="result-label">Final answer</div>
              <div class="result-text" [innerHTML]="renderMarkdown(item.text)"></div>
              <div class="result-meta">
                @if (item.turns !== undefined) {
                  <span>{{ item.turns }} turn{{ item.turns === 1 ? '' : 's' }}</span>
                }
                @if (item.durationMs !== undefined) {
                  <span>· {{ (item.durationMs / 1000).toFixed(1) }}s</span>
                }
                @if (item.cost !== undefined) {
                  <span>· \${{ item.cost.toFixed(4) }}</span>
                }
              </div>
            </div>
          }
          @case ('error') {
            <div class="item item-error-msg">⚠ {{ item.text }}</div>
          }
        }
      }

      @if (answerId()) {
        <app-feedback-panel
          [answerId]="answerId()"
          [question]="currentQuestion()"
          [sources]="wikiSources()"
        />
      }

      <div #scrollAnchor></div>
    </div>
  `,
  styleUrl: './agent-transcript.scss',
})
export class AgentTranscript implements OnDestroy {
  private api = inject(ApiService);

  @ViewChild('scrollAnchor') scrollAnchor?: ElementRef<HTMLDivElement>;

  items = signal<TranscriptItem[]>([]);
  status = signal<Status>('idle');
  error = signal<string>('');
  currentQuestion = signal<string>('');
  answerId = signal<string>('');
  wikiSources = signal<string[]>([]);
  conversationId = signal<string>('');

  /**
   * Parent assigns a request to trigger a stream. When the value changes
   * (object identity), the transcript automatically starts a new stream.
   * Pass `null` to keep the transcript idle.
   */
  request = input<AgentRequest | null>(null);

  // Emit when the stream finishes (success or error) — parent can refresh
  // the conversation list and message log.
  completed = output<{ conversationId: string; success: boolean }>();

  private sub?: Subscription;
  private serverScope: 'com' | 'in' = 'com';
  private buidScope: string | undefined;
  private lastHandledRequest: AgentRequest | null = null;

  constructor() {
    // Auto-scroll the transcript to the latest item while streaming.
    effect(() => {
      // Track items and status (read both to register dependencies).
      this.items();
      const live = this.status() === 'streaming';
      if (!live) return;
      queueMicrotask(() => this.scrollToBottom());
    });

    // Start a new stream whenever the parent sets a new request.
    // Object-identity comparison so the same request never fires twice.
    effect(() => {
      const req = this.request();
      if (!req) return;
      if (req === this.lastHandledRequest) return;
      this.lastHandledRequest = req;
      untracked(() => this.start(req));
    });
  }

  // ── Public API ─────────────────────────────────────────────────────────

  start(opts: AgentRequest): void {
    this.stop();
    this.items.set([]);
    this.error.set('');
    this.answerId.set('');
    this.wikiSources.set([]);
    this.currentQuestion.set(opts.question);
    this.conversationId.set(opts.conversationId ?? '');
    this.serverScope = opts.server ?? 'com';
    this.buidScope = opts.buid;
    this.status.set('streaming');

    this.sub = this.api
      .streamQuery({
        question: opts.question,
        conversation_id: opts.conversationId,
        server: this.serverScope,
        buid: this.buidScope,
      })
      .subscribe({
        next: evt => this.handleEvent(evt),
        error: err => {
          this.error.set(String(err?.message ?? err));
          this.status.set('error');
          this.completed.emit({ conversationId: this.conversationId(), success: false });
        },
      });
  }

  stop(): void {
    this.sub?.unsubscribe();
    this.sub = undefined;
    if (this.status() === 'streaming') {
      this.status.set('idle');
    }
  }

  isStreaming(): boolean {
    return this.status() === 'streaming';
  }

  ngOnDestroy(): void {
    this.stop();
  }

  private scrollToBottom(): void {
    const el = this.scrollAnchor?.nativeElement;
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }

  private logAnswerForFeedback(answerText: string): void {
    if (!answerText.trim()) {
      this.completed.emit({ conversationId: this.conversationId(), success: true });
      return;
    }
    const toolCalls = this.items()
      .filter((i): i is ToolItem => i.kind === 'tool')
      .map(t => ({ name: t.name, input: t.input }));

    this.api
      .logAgentAnswer({
        question: this.currentQuestion(),
        answer_text: answerText,
        tool_calls: toolCalls,
        conversation_id: this.conversationId() || undefined,
        server: this.serverScope,
        buid: this.buidScope,
      })
      .subscribe({
        next: r => {
          this.answerId.set(r.answer_id);
          this.wikiSources.set(r.wiki_pages ?? []);
          this.completed.emit({ conversationId: this.conversationId(), success: true });
        },
        error: () => {
          this.completed.emit({ conversationId: this.conversationId(), success: true });
        },
      });
  }

  // ── Event dispatch ─────────────────────────────────────────────────────

  private handleEvent(evt: AgentEvent): void {
    switch (evt.type) {
      case 'system': {
        const e = evt as Record<string, any>;
        if (e['subtype'] === 'init') {
          this.append({
            kind: 'init',
            cwd: e['cwd'],
            toolCount: Array.isArray(e['tools']) ? e['tools'].length : undefined,
            mcpCount: Array.isArray(e['mcp_servers']) ? e['mcp_servers'].length : undefined,
            model: e['model'],
          });
        }
        break;
      }
      case 'assistant': {
        const blocks = (evt as any).message?.content ?? [];
        this.handleAssistantContent(blocks as ContentBlock[]);
        break;
      }
      case 'user': {
        const blocks = (evt as any).message?.content ?? [];
        this.handleUserContent(blocks as ContentBlock[]);
        break;
      }
      case 'result': {
        const e = evt as Record<string, any>;
        const text = String(e['result'] ?? '');
        this.append({
          kind: 'result',
          text,
          turns: e['num_turns'],
          durationMs: e['duration_ms'],
          cost: e['total_cost_usd'],
          isError: Boolean(e['is_error']),
        });
        this.status.set(e['is_error'] ? 'error' : 'done');
        if (!e['is_error']) {
          this.logAnswerForFeedback(text);
        }
        break;
      }
      case 'error': {
        const e = evt as Record<string, any>;
        this.append({
          kind: 'error',
          text: String(e['error'] ?? e['stderr'] ?? 'unknown error'),
        });
        this.status.set('error');
        break;
      }
      case 'rate_limit_event':
        // Silent — surfacing this would be noisy
        break;
      case '__conversation': {
        const id = (evt as any).conversation_id;
        if (id) this.conversationId.set(String(id));
        break;
      }
      case '__done':
        if (this.status() === 'streaming') this.status.set('done');
        break;
      case '__sse_error': {
        const msg = (evt as any).error ?? 'Stream transport error';
        this.error.set(String(msg));
        this.status.set('error');
        this.completed.emit({ conversationId: this.conversationId(), success: false });
        break;
      }
      default:
        // Unknown event types pass through silently
        break;
    }
  }

  private handleAssistantContent(blocks: ContentBlock[]): void {
    for (const block of blocks) {
      if (block.type === 'text') {
        if (block.text.trim().length > 0) {
          this.append({ kind: 'text', text: block.text });
        }
      } else if (block.type === 'thinking') {
        this.append({ kind: 'thinking', text: block.thinking });
      } else if (block.type === 'tool_use') {
        this.append({
          kind: 'tool',
          id: block.id,
          name: block.name,
          input: block.input,
          pending: true,
          expanded: false,
        });
      }
    }
  }

  private handleUserContent(blocks: ContentBlock[]): void {
    for (const block of blocks) {
      if (block.type !== 'tool_result') continue;

      let resultText = '';
      if (typeof block.content === 'string') {
        resultText = block.content;
      } else if (Array.isArray(block.content)) {
        resultText = block.content
          .map(c => (c.type === 'text' ? (c as any).text : JSON.stringify(c)))
          .join('\n');
      }

      const id = block.tool_use_id;
      const isError = Boolean(block.is_error);
      this.items.update(arr =>
        arr.map(it =>
          it.kind === 'tool' && it.id === id
            ? { ...it, result: resultText, pending: false, isError }
            : it,
        ),
      );
    }
  }

  // ── Template helpers ───────────────────────────────────────────────────

  toggleTool(id: string): void {
    this.items.update(arr =>
      arr.map(it =>
        it.kind === 'tool' && it.id === id ? { ...it, expanded: !it.expanded } : it,
      ),
    );
  }

  toolIcon(name: string): string {
    const map: Record<string, string> = {
      Read: '📄',
      Write: '✏️',
      Edit: '✏️',
      Bash: '$',
      Grep: '🔍',
      Glob: '📁',
      WebFetch: '🌐',
      WebSearch: '🔎',
      Task: '🤖',
      TodoWrite: '📝',
      NotebookEdit: '📓',
    };
    return map[name] ?? '🔧';
  }

  toolInputSummary(item: ToolItem): string {
    const input = (item.input ?? {}) as Record<string, unknown>;
    if (input['file_path']) return String(input['file_path']);
    if (input['path']) return String(input['path']);
    if (input['pattern']) return String(input['pattern']);
    if (input['command']) return String(input['command']).slice(0, 100);
    if (input['url']) return String(input['url']);
    if (input['query']) return String(input['query']);
    if (input['description']) return String(input['description']);
    const keys = Object.keys(input);
    if (keys.length === 0) return '';
    return keys
      .slice(0, 3)
      .map(k => `${k}=${String((input as any)[k]).slice(0, 30)}`)
      .join(' ');
  }

  formatJson(obj: unknown): string {
    try {
      return JSON.stringify(obj, null, 2);
    } catch {
      return String(obj);
    }
  }

  renderMarkdown(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/^### (.+)$/gm, '<h4>$1</h4>')
      .replace(/^## (.+)$/gm, '<h3>$1</h3>')
      .replace(/^# (.+)$/gm, '<h2>$1</h2>')
      .replace(/\n/g, '<br>');
  }

  // ── Private ────────────────────────────────────────────────────────────

  private append(item: TranscriptItem): void {
    this.items.update(arr => [...arr, item]);
  }
}
