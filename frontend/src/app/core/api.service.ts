import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';

export type QueryMode = 'api' | 'claude-code' | 'agent';

export interface QueryRequest {
  question: string;
  mode?: QueryMode;
  server: 'com' | 'in';
  buid?: string;
  functional_area?: string;
  service?: string;
  officeid?: string;
  roomid?: string;
  role?: string;
  conversation_id?: string;
}

export interface SourceInfo {
  wiki_pages: string[];
  jira_keys: string[];
  pms_configs: string[];
}

export interface ToolTraceEntry {
  round: number;
  tool_name: string;
  input: Record<string, unknown>;
  output_summary: string;
}

export interface QueryResponse {
  answer_id: string;
  answer_text: string;
  confidence: 'High' | 'Medium' | 'Low';
  sources: SourceInfo;
  retrieval: Record<string, unknown>;
  mode: QueryMode;
  error: string;
  tool_trace: ToolTraceEntry[];
  missing_context: string[];
  deep_search_used: boolean;
  conversation_id?: string;
}

// ── Conversations / chat history ───────────────────────────────────────────

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  mode?: string | null;
  server?: string | null;
  buid?: string | null;
  answer_id?: string | null;
  confidence?: string | null;
  sources?: SourceInfo | null;
  tool_trace?: ToolTraceEntry[] | null;
  missing_context?: string[] | null;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export interface JiraTicket {
  key: string;
  summary: string;
  status: string;
  updated: string;
  resolved: string | null;
  comment_count: number;
  hit_summary: boolean;
}

export interface SearchResponse {
  wiki_pages: { path: string; title: string; excerpt: string }[];
  jira_markdown: string;
  jira_buckets: { LATEST: JiraTicket[]; HISTORICAL: JiraTicket[]; 'STALE-OPEN': JiraTicket[] };
  jira_keywords: string[];
}

export interface FeedbackRequest {
  answer_id: string;
  question: string;
  score: number;
  label: string;
  correction?: string;
  expected_answer?: string;
  sources?: string[];
  affected?: string[];
  reviewer?: string;
}

export interface WikiPage {
  path: string;
  title: string;
  content: string;
}

export interface OperationalStatus {
  jira_mirror_age_hours: number | null;
  last_successful_sync: string | null;
  wiki_page_count: number;
  pending_admin_review_count: number;
}

export type ProposalType = 'new' | 'edit' | 'append' | 'multi_edit' | 'legacy_text';
export type ProposalStatus = 'pending' | 'applied' | 'rejected';

export interface CompanionEdit {
  kind: string;
  field: string;
  edits: { page_path: string; reciprocal_field: string; add: string | null; remove: string | null }[];
  note: string;
}

export interface WikiProposal {
  id: string;
  proposal_type: ProposalType;
  status: ProposalStatus;
  submitter_email: string;
  reason: string;
  answer_id: string | null;
  created_at: string;
  resolved_at: string | null;
  applied_at: string | null;
  applied_by: string | null;
  admin_note: string | null;
  validation_log: string[];
  suggested_companion_edit: CompanionEdit | null;
  // Type-specific fields
  page_path?: string;
  content?: string;
  old_string?: string;
  new_string?: string;
  edits?: { page_path: string; old_string: string; new_string: string }[];
  // Legacy-text only
  proposed_change?: string;
}

export interface ProposalApplyResult {
  success: boolean;
  code?: string;
  message?: string;
  files_written?: string[];
  rollback_status?: string;
  error?: string;
}

// ── Claude Code Agent streaming (NDJSON over SSE) ──────────────────────────

export type ContentBlock =
  | { type: 'text'; text: string }
  | { type: 'thinking'; thinking: string }
  | {
      type: 'tool_use';
      id: string;
      name: string;
      input: Record<string, unknown>;
    }
  | {
      type: 'tool_result';
      tool_use_id: string;
      content: string | ContentBlock[];
      is_error?: boolean;
    };

export interface SystemInitEvent {
  type: 'system';
  subtype: 'init' | string;
  cwd?: string;
  session_id?: string;
  model?: string;
  tools?: string[];
  mcp_servers?: { name: string; status: string }[];
  [k: string]: unknown;
}

export interface AssistantEvent {
  type: 'assistant';
  message: {
    id?: string;
    model?: string;
    content: ContentBlock[];
    stop_reason?: string | null;
    [k: string]: unknown;
  };
  session_id?: string;
  parent_tool_use_id?: string | null;
  [k: string]: unknown;
}

export interface UserEvent {
  type: 'user';
  message: {
    content: ContentBlock[];
    [k: string]: unknown;
  };
  session_id?: string;
  [k: string]: unknown;
}

export interface ResultEvent {
  type: 'result';
  subtype: 'success' | 'error_max_turns' | string;
  result?: string;
  is_error?: boolean;
  duration_ms?: number;
  duration_api_ms?: number;
  num_turns?: number;
  total_cost_usd?: number;
  session_id?: string;
  [k: string]: unknown;
}

export interface RateLimitEvent {
  type: 'rate_limit_event';
  rate_limit_info?: Record<string, unknown>;
  [k: string]: unknown;
}

export interface StreamErrorEvent {
  type: 'error';
  error?: string;
  returncode?: number;
  stderr?: string;
  [k: string]: unknown;
}

export interface RawEvent {
  type: 'raw';
  line: string;
}

export interface SseDoneSignal {
  type: '__done';
}

export interface SseErrorSignal {
  type: '__sse_error';
  error: string;
}

export interface SseConversationSignal {
  type: '__conversation';
  conversation_id: string;
}

export type AgentEvent =
  | SystemInitEvent
  | AssistantEvent
  | UserEvent
  | ResultEvent
  | RateLimitEvent
  | StreamErrorEvent
  | RawEvent
  | SseDoneSignal
  | SseErrorSignal
  | SseConversationSignal
  | { type: string; [k: string]: unknown };

export interface SyncStatus {
  jira: { last_sync_line: string; ticket_count: number };
  drive: { last_sync: string; file_count: number };
  feedback: { pending_count: number };
}

export interface IngestItem {
  module: string;
  path: string;
  error?: string;
}

export interface FeedbackRecord {
  feedback_id: string;
  answer_id: string;
  question: string;
  score: number;
  label: string;
  correction: string;
  affected: string[];
  status: string;
  created_at: string;
}

const API_BASE = 'http://localhost:8000';
const ADMIN_TOKEN_KEY = 'conwo_admin_token';
const MODE_STORAGE = 'conwo_query_mode';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);

  // ── API key (stored in localStorage) ──────────────────────────────────

  getAdminToken(): string {
    return localStorage.getItem(ADMIN_TOKEN_KEY) ?? '';
  }

  setAdminToken(token: string): void {
    localStorage.setItem(ADMIN_TOKEN_KEY, token);
  }

  isAdmin(): boolean {
    return !!this.getAdminToken();
  }

  getStoredMode(): QueryMode {
    const v = localStorage.getItem(MODE_STORAGE);
    if (v === 'claude-code' || v === 'agent') return v;
    return 'api';
  }

  setMode(mode: QueryMode): void {
    localStorage.setItem(MODE_STORAGE, mode);
  }

  // ── Query ──────────────────────────────────────────────────────────────

  query(req: QueryRequest): Observable<QueryResponse> {
    const token = this.getAdminToken();
    const headers = token
      ? new HttpHeaders({ Authorization: `Bearer ${token}` })
      : new HttpHeaders();
    return this.http.post<QueryResponse>(`${API_BASE}/query`, req, { headers });
  }

  /**
   * Stream a Claude Code agent session over SSE.
   *
   * Emits one AgentEvent per server frame. Synthesizes a `__done` event when the
   * server closes the stream cleanly, and `__sse_error` on transport failure.
   * Unsubscribing aborts the underlying fetch — the backend will SIGTERM the
   * subprocess in response.
   *
   * Requires a Bearer admin token in localStorage.
   */
  streamQuery(req: {
    question: string;
    conversation_id?: string;
    server?: 'com' | 'in';
    buid?: string;
  }): Observable<AgentEvent> {
    return new Observable<AgentEvent>(subscriber => {
      const ctrl = new AbortController();
      const token = this.getAdminToken();

      fetch(`${API_BASE}/query/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: token ? `Bearer ${token}` : '',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({
          question: req.question,
          conversation_id: req.conversation_id ?? null,
          server: req.server ?? 'com',
          buid: req.buid ?? null,
        }),
        signal: ctrl.signal,
      })
        .then(async resp => {
          if (!resp.ok) {
            let detail = `HTTP ${resp.status}`;
            try {
              const body = await resp.json();
              if (body?.detail) detail = String(body.detail);
            } catch {
              /* non-JSON body */
            }
            subscriber.next({ type: '__sse_error', error: detail });
            subscriber.complete();
            return;
          }
          if (!resp.body) {
            subscriber.next({ type: '__sse_error', error: 'No response body' });
            subscriber.complete();
            return;
          }

          const reader = resp.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            // SSE frames are separated by a blank line ("\n\n").
            let sep: number;
            while ((sep = buffer.indexOf('\n\n')) !== -1) {
              const frame = buffer.slice(0, sep);
              buffer = buffer.slice(sep + 2);
              const parsed = parseSseFrame(frame);
              if (parsed) subscriber.next(parsed);
            }
          }
          subscriber.next({ type: '__done' });
          subscriber.complete();
        })
        .catch(err => {
          if (err?.name === 'AbortError') {
            subscriber.complete();
            return;
          }
          subscriber.next({ type: '__sse_error', error: String(err?.message ?? err) });
          subscriber.complete();
        });

      return () => ctrl.abort();
    });
  }

  logAgentAnswer(req: {
    question: string;
    answer_text: string;
    tool_calls: Array<{ name: string; input: Record<string, unknown> }>;
    conversation_id?: string;
    server?: string;
    buid?: string;
  }): Observable<{
    answer_id: string;
    confidence: string;
    wiki_pages: string[];
    jira_keys: string[];
  }> {
    const token = this.getAdminToken();
    const headers = token
      ? new HttpHeaders({ Authorization: `Bearer ${token}` })
      : new HttpHeaders();
    return this.http.post<{
      answer_id: string;
      confidence: string;
      wiki_pages: string[];
      jira_keys: string[];
    }>(`${API_BASE}/agent/log-answer`, req, { headers });
  }

  checkClaudeCodeHealth(): Observable<{
    available: boolean;
    local_dev_unauthenticated: boolean;
    note: string;
  }> {
    return this.http.get<{
      available: boolean;
      local_dev_unauthenticated: boolean;
      note: string;
    }>(`${API_BASE}/health/claude-code`);
  }

  search(question: string, server: 'com' | 'in' = 'com'): Observable<SearchResponse> {
    return this.http.post<SearchResponse>(`${API_BASE}/search`, { question, server });
  }

  getWikiPage(path: string): Observable<WikiPage> {
    return this.http.get<WikiPage>(`${API_BASE}/wiki/${path}`);
  }

  // ── Conversations ──────────────────────────────────────────────────────

  listConversations(): Observable<{ conversations: ConversationSummary[] }> {
    return this.http.get<{ conversations: ConversationSummary[] }>(`${API_BASE}/conversations`);
  }

  getConversation(id: string): Observable<Conversation> {
    return this.http.get<Conversation>(`${API_BASE}/conversations/${id}`);
  }

  createConversation(title?: string): Observable<ConversationSummary> {
    return this.http.post<ConversationSummary>(
      `${API_BASE}/conversations`,
      { title: title ?? null },
    );
  }

  renameConversation(id: string, title: string): Observable<{ id: string; title: string; updated_at: string }> {
    return this.http.patch<{ id: string; title: string; updated_at: string }>(
      `${API_BASE}/conversations/${id}`,
      { title },
    );
  }

  deleteConversation(id: string): Observable<{ deleted: boolean; id: string }> {
    return this.http.delete<{ deleted: boolean; id: string }>(`${API_BASE}/conversations/${id}`);
  }

  // ── Feedback ───────────────────────────────────────────────────────────

  submitFeedback(req: FeedbackRequest): Observable<{ feedback_id: string; status: string }> {
    return this.http.post<{ feedback_id: string; status: string }>(`${API_BASE}/feedback`, req);
  }

  // ── Operational status (chat-page banner; any authenticated user) ─────

  getStatus(): Observable<OperationalStatus> {
    const token = this.getAdminToken();
    const headers = token
      ? new HttpHeaders({ Authorization: `Bearer ${token}` })
      : new HttpHeaders();
    return this.http.get<OperationalStatus>(`${API_BASE}/status`, { headers });
  }

  // ── Admin ──────────────────────────────────────────────────────────────

  private adminHeaders(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.getAdminToken()}` });
  }

  getSyncStatus(): Observable<SyncStatus> {
    return this.http.get<SyncStatus>(`${API_BASE}/admin/sync-status`, { headers: this.adminHeaders() });
  }

  triggerSync(): Observable<{ status: string; pid?: number }> {
    return this.http.post<{ status: string; pid?: number }>(`${API_BASE}/admin/trigger-sync`, {}, { headers: this.adminHeaders() });
  }

  getIngestQueue(): Observable<IngestItem[]> {
    return this.http.get<IngestItem[]>(`${API_BASE}/admin/ingest-queue`, { headers: this.adminHeaders() });
  }

  getFeedbackList(status = 'pending'): Observable<FeedbackRecord[]> {
    return this.http.get<FeedbackRecord[]>(`${API_BASE}/admin/feedback?status=${status}`, { headers: this.adminHeaders() });
  }

  getPatchPlan(feedbackId: string): Observable<{ plan: string; dry_run: boolean }> {
    return this.http.post<{ plan: string; dry_run: boolean }>(
      `${API_BASE}/admin/feedback/${feedbackId}/patch-plan`, {},
      { headers: this.adminHeaders() }
    );
  }

  applyPatch(feedbackId: string): Observable<{ success: boolean; output: string }> {
    return this.http.post<{ success: boolean; output: string }>(
      `${API_BASE}/admin/feedback/${feedbackId}/apply`, {},
      { headers: this.adminHeaders() }
    );
  }

  // ── Wiki proposals (Track A) ───────────────────────────────────────────

  listProposals(status?: ProposalStatus): Observable<{ proposals: WikiProposal[] }> {
    const url = status
      ? `${API_BASE}/admin/wiki/proposals?status=${status}`
      : `${API_BASE}/admin/wiki/proposals`;
    return this.http.get<{ proposals: WikiProposal[] }>(url, { headers: this.adminHeaders() });
  }

  applyProposal(id: string): Observable<ProposalApplyResult> {
    return this.http.post<ProposalApplyResult>(
      `${API_BASE}/admin/wiki/proposals/${id}/apply`, {},
      { headers: this.adminHeaders() }
    );
  }

  markProposalApplied(id: string): Observable<ProposalApplyResult> {
    return this.http.post<ProposalApplyResult>(
      `${API_BASE}/admin/wiki/proposals/${id}/mark-applied`, {},
      { headers: this.adminHeaders() }
    );
  }

  rejectProposal(id: string, admin_note?: string): Observable<ProposalApplyResult> {
    return this.http.post<ProposalApplyResult>(
      `${API_BASE}/admin/wiki/proposals/${id}/reject`,
      { admin_note: admin_note ?? '' },
      { headers: this.adminHeaders() }
    );
  }

  health(): Observable<{ status: string; wiki_pages: number; has_server_key: boolean }> {
    return this.http.get<{ status: string; wiki_pages: number; has_server_key: boolean }>(`${API_BASE}/health`);
  }
}

/**
 * Parse a single SSE frame into an AgentEvent.
 *
 * Frame shapes we handle:
 *   data: {json}              → returns the parsed dict
 *   event: done\ndata: {}     → returns { type: '__done' }
 *   event: error\ndata: {...} → returns { type: '__sse_error', error: ... }
 *   <unknown>                 → returns null (skipped)
 */
function parseSseFrame(frame: string): AgentEvent | null {
  const lines = frame.split('\n').filter(l => l.length > 0);
  let eventName = '';
  let dataPayload = '';
  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataPayload += line.slice(5).trimStart();
    }
  }

  if (eventName === 'done') return { type: '__done' };

  if (eventName === 'error') {
    try {
      const parsed = JSON.parse(dataPayload || '{}');
      return { type: '__sse_error', error: String(parsed?.error ?? 'unknown error') };
    } catch {
      return { type: '__sse_error', error: dataPayload || 'unknown error' };
    }
  }

  if (eventName === 'conversation') {
    try {
      const parsed = JSON.parse(dataPayload || '{}');
      return { type: '__conversation', conversation_id: String(parsed?.conversation_id ?? '') };
    } catch {
      return null;
    }
  }

  if (!dataPayload) return null;
  try {
    return JSON.parse(dataPayload) as AgentEvent;
  } catch {
    return { type: 'raw', line: dataPayload };
  }
}
