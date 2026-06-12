/**
 * ChatSidebar — presentational list of past conversations.
 *
 * Renders only the scrollable conversation list. The surrounding chrome
 * (the "New chat" button, collapse control, mobile behaviour, sidebar frame)
 * is owned by the parent <app-sidebar>. State is pushed in via inputs; this
 * component emits intent events and never calls the API itself.
 */
import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConversationSummary } from '../../core/api.service';

@Component({
  selector: 'app-chat-sidebar',
  imports: [CommonModule],
  template: `
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
  `,
  styles: [`
    :host { display: contents; }

    .chat-list {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      overscroll-behavior: contain;
      padding: 4px 6px;
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
      cursor: pointer;
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
      cursor: pointer;
      transition: opacity 0.15s, color 0.15s;

      &:hover { color: var(--error); }
      &:focus-visible {
        opacity: 1;
        outline: 2px solid var(--accent-ring);
        outline-offset: -2px;
      }
    }
  `]
})
export class ChatSidebar {
  conversations = input<ConversationSummary[]>([]);
  activeId = input<string | null>(null);
  loading = input<boolean>(false);

  openChat = output<string>();
  deleteChat = output<string>();

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
