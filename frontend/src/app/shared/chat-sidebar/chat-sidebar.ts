/**
 * ChatSidebar — collapsible left rail showing past conversations.
 *
 * The Ask page owns conversation state and pushes ConversationSummary[] in.
 * This component emits intent events; it does not call the API itself.
 */
import { Component, OnInit, input, output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, ConversationSummary } from '../../core/api.service';

@Component({
  selector: 'app-chat-sidebar',
  imports: [CommonModule],
  template: `
    <aside class="sidebar" [class.collapsed]="collapsed()">
      <div class="sidebar-head">
        <button class="new-btn" type="button" (click)="newChat.emit()">
          <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
            <path d="M8 3v10 M3 8h10" fill="none" stroke="currentColor"
                  stroke-width="1.5" stroke-linecap="round" />
          </svg>
          New chat
        </button>
        <button
          class="collapse-btn"
          type="button"
          (click)="collapsed.set(!collapsed())"
          [attr.aria-label]="collapsed() ? 'Expand sidebar' : 'Collapse sidebar'"
          [title]="collapsed() ? 'Expand sidebar' : 'Collapse sidebar'"
        >
          <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
            @if (collapsed()) {
              <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
            } @else {
              <path d="M10 4l-4 4 4 4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
            }
          </svg>
        </button>
      </div>

      @if (!collapsed()) {
        <nav class="chat-list" aria-label="Past conversations">
          @if (loading()) {
            <div class="empty">Loading…</div>
          } @else if (conversations().length === 0) {
            <div class="empty">No chats yet. Start a new conversation.</div>
          } @else {
            @for (c of conversations(); track c.id) {
              <div
                class="chat-item"
                [class.active]="c.id === activeId()"
                (click)="openChat.emit(c.id)"
              >
                <button class="chat-title-btn" type="button" [title]="c.title">
                  <span class="chat-title">{{ c.title }}</span>
                  <span class="chat-sub">{{ c.message_count }} msg · {{ formatDate(c.updated_at) }}</span>
                </button>
                <button
                  class="chat-del-btn"
                  type="button"
                  (click)="$event.stopPropagation(); confirmDelete(c)"
                  [attr.aria-label]="'Delete ' + c.title"
                  title="Delete chat"
                >
                  <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
                    <path d="M4 4l8 8 M12 4l-8 8" fill="none" stroke="currentColor"
                          stroke-width="1.5" stroke-linecap="round" />
                  </svg>
                </button>
              </div>
            }
          }
        </nav>
      }
    </aside>
  `,
  styles: [`
    :host { display: contents; }

    .sidebar {
      width: 260px;
      flex-shrink: 0;
      background: rgba(255, 254, 251, 0.92);
      backdrop-filter: saturate(140%) blur(18px);
      -webkit-backdrop-filter: saturate(140%) blur(18px);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      min-height: 0;
      transition: width 0.2s;
    }
    .sidebar.collapsed { width: 56px; }

    .sidebar-head {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
    }

    .new-btn {
      flex: 1;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      background: var(--accent);
      color: var(--text-on-accent);
      border: none;
      border-radius: var(--radius-sm);
      padding: 7px 10px;
      font-size: 0.82rem;
      font-weight: 500;
      transition: background 0.15s;

      &:hover { background: var(--accent-hover); }
    }

    .sidebar.collapsed .new-btn {
      padding: 7px;
      span, svg { display: none; }
      &::after {
        content: '+';
        font-size: 1rem;
        font-weight: 600;
        line-height: 1;
      }
    }

    .collapse-btn {
      background: none;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      width: 28px;
      height: 28px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: var(--text-muted);

      &:hover { background: var(--surface-muted); color: var(--text); }
    }

    .chat-list {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      overscroll-behavior: contain;
      padding: 8px 6px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .empty {
      padding: 14px;
      color: var(--text-subtle);
      font-size: 0.82rem;
      text-align: center;
    }

    .chat-item {
      position: relative;
      display: flex;
      align-items: stretch;
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: background 0.12s;

      &:hover {
        background: var(--surface-muted);
        .chat-del-btn { opacity: 1; }
      }

      &.active {
        background: var(--surface-muted);
        .chat-title { color: var(--text); font-weight: 600; }
      }
    }

    .chat-title-btn {
      flex: 1;
      background: none;
      border: none;
      text-align: left;
      padding: 8px 10px;
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }

    .chat-title {
      font-size: 0.85rem;
      color: var(--text);
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
      max-width: 100%;
    }

    .chat-sub {
      font-size: 0.7rem;
      color: var(--text-subtle);
      font-family: var(--font-mono);
    }

    .chat-del-btn {
      opacity: 0;
      background: none;
      border: none;
      padding: 0 8px;
      color: var(--text-subtle);
      transition: opacity 0.15s, color 0.15s;

      &:hover { color: var(--error); }
      &:focus-visible {
        opacity: 1;
        outline: 2px solid var(--accent-ring);
        outline-offset: -2px;
      }
    }

    @media (max-width: 720px) {
      .sidebar { width: 56px; }
      .sidebar:not(.collapsed) {
        position: fixed;
        top: 56px;
        bottom: 0;
        left: 0;
        z-index: 50;
        width: 260px;
        box-shadow: var(--shadow);
      }
    }
  `]
})
export class ChatSidebar implements OnInit {
  private api = inject(ApiService);

  conversations = input<ConversationSummary[]>([]);
  activeId = input<string | null>(null);
  loading = input<boolean>(false);

  newChat = output<void>();
  openChat = output<string>();
  deleteChat = output<string>();

  collapsed = signal(false);

  ngOnInit(): void {
    // remember collapsed state across sessions
    const stored = localStorage.getItem('conwo_sidebar_collapsed');
    if (stored === '1') this.collapsed.set(true);
  }

  toggleCollapse(): void {
    const next = !this.collapsed();
    this.collapsed.set(next);
    localStorage.setItem('conwo_sidebar_collapsed', next ? '1' : '0');
  }

  formatDate(iso: string): string {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffHours = diffMs / (1000 * 60 * 60);
      if (diffHours < 24) {
        return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
      }
      const diffDays = Math.floor(diffHours / 24);
      if (diffDays < 7) return `${diffDays}d`;
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  }

  confirmDelete(c: ConversationSummary): void {
    if (confirm(`Delete "${c.title}"? This cannot be undone.`)) {
      this.deleteChat.emit(c.id);
    }
  }
}
