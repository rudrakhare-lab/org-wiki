/**
 * ConversationStore — app-wide conversation state.
 *
 * Previously the Ask page owned the conversation list + active selection and
 * fed them into <app-chat-sidebar>. Now the sidebar lives in the global app
 * shell (app-sidebar), so the list/active id are hoisted here as a singleton
 * the shell and the Ask page both inject.
 *
 * This store owns the conversation *list* and which one is active. It does NOT
 * own the message thread — that stays in the Ask page, which reacts to
 * `activeId` via an effect() and loads/clears its own `messages`.
 */
import { Injectable, inject, signal } from '@angular/core';
import { ApiService, ConversationSummary } from './api.service';

@Injectable({ providedIn: 'root' })
export class ConversationStore {
  private api = inject(ApiService);

  readonly conversations = signal<ConversationSummary[]>([]);
  readonly activeId = signal<string | null>(null);
  readonly loading = signal(false);

  /** Reload the conversation list from the server (best-effort). */
  refresh(): void {
    this.loading.set(true);
    this.api.listConversations().subscribe({
      next: (r) => {
        this.conversations.set(r.conversations);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  /** Select a conversation — the Ask page reacts and loads its messages. */
  open(id: string): void {
    this.activeId.set(id);
  }

  /** Start a fresh conversation (clears the active selection). */
  newChat(): void {
    this.activeId.set(null);
  }

  /**
   * Set the active id directly. Used by the Ask page after it has itself
   * created/loaded a conversation, so its effect() no-ops instead of re-fetching.
   */
  setActive(id: string | null): void {
    this.activeId.set(id);
  }

  /** Clear all state — call on sign-out so a re-login starts clean. */
  reset(): void {
    this.conversations.set([]);
    this.activeId.set(null);
    this.loading.set(false);
  }

  /** Delete a conversation; if it was active, fall back to a new chat. */
  delete(id: string): void {
    this.api.deleteConversation(id).subscribe({
      next: () => {
        if (this.activeId() === id) this.activeId.set(null);
        this.refresh();
      },
      error: () => {
        /* best-effort — surfaced via the confirm dialog gate before this call */
      },
    });
  }
}
