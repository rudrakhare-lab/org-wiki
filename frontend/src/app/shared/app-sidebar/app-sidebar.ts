/**
 * AppSidebar — the single, Claude-style left sidebar for the app shell.
 *
 * Layout (top → bottom): brand + collapse · "New chat" · primary nav (icons +
 * labels, Admin gated on role) · "Recent" conversation list · user identity +
 * Sign out. Collapses to an icon rail on desktop (persisted) and slides in
 * off-canvas on mobile via the hamburger.
 *
 * Conversation state comes from ConversationStore (shared with the Ask page);
 * sign-out is delegated to the shell via the (signOut) output so the shell
 * stays the owner of auth/session signals.
 */
import { Component, OnInit, inject, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { ConversationStore } from '../../core/conversation.store';
import { ChatSidebar } from '../chat-sidebar/chat-sidebar';
import { AgentService } from '../../core/agent.service';

const COLLAPSE_KEY = 'conwo_sidebar_collapsed';

interface NavItem {
  label: string;
  route: string;
  icon: string;
  roles: string[];   // roles allowed to see this item
}

const KNOWN_ROLES = ['admin', 'developer', 'general'];

@Component({
  selector: 'app-sidebar',
  imports: [CommonModule, RouterLink, RouterLinkActive, ChatSidebar],
  template: `
    <button
      class="hamburger"
      type="button"
      (click)="mobileOpen.set(true)"
      aria-label="Open navigation"
    >
      <svg viewBox="0 0 16 16" width="18" height="18" fill="none" stroke="currentColor"
           stroke-width="1.6" stroke-linecap="round">
        <path d="M2.5 4.5h11M2.5 8h11M2.5 11.5h11" />
      </svg>
    </button>

    <aside class="sidebar" [class.collapsed]="collapsed()" [class.mobile-open]="mobileOpen()">
      <!-- Brand + collapse -->
      <div class="sb-head">
        <div class="sb-agent">
          <a routerLink="/ask" class="sb-brand" (click)="closeMobile()" [attr.aria-label]="agentSvc.activeName() + ' — home'">
            <img src="logo.png" alt="" class="sb-logo" />
            <span class="sb-name sb-label">{{ agentSvc.activeName() }}</span>
          </a>
          @if (agentSvc.agents().length > 1) {
            <button class="sb-agent-toggle sb-label" type="button"
                    (click)="agentMenuOpen.set(!agentMenuOpen())"
                    [attr.aria-expanded]="agentMenuOpen()" aria-label="Switch agent" title="Switch agent">
              <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6l4 4 4-4"/></svg>
            </button>
          }
          @if (agentMenuOpen()) {
            <div class="sb-agent-menu">
              @for (a of agentSvc.agents(); track a.id) {
                <button type="button" class="sb-agent-item"
                        [class.active]="a.id === agentSvc.activeId()"
                        (click)="onSelectAgent(a.id)">
                  <span class="sb-agent-item-name">{{ a.display_name }}</span>
                  <span class="sb-agent-item-desc">{{ a.description }}</span>
                </button>
              }
            </div>
          }
        </div>
        <button
          class="sb-collapse"
          type="button"
          (click)="toggleCollapse()"
          [attr.aria-label]="collapsed() ? 'Expand sidebar' : 'Collapse sidebar'"
          [title]="collapsed() ? 'Expand sidebar' : 'Collapse sidebar'"
        >
          <svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor"
               stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            @if (collapsed()) {
              <path d="M6 4l4 4-4 4" />
            } @else {
              <path d="M10 4l-4 4 4 4" />
            }
          </svg>
        </button>
      </div>

      <!-- New chat -->
      <button class="sb-new" type="button" (click)="onNewChat()" title="New chat">
        <svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor"
             stroke-width="1.6" stroke-linecap="round">
          <path d="M8 3.5v9M3.5 8h9" />
        </svg>
        <span class="sb-label">New chat</span>
      </button>

      <!-- Primary nav -->
      <nav class="sb-nav" aria-label="Primary">
        @for (item of visibleNav(); track item.route) {
          <a
            [routerLink]="item.route"
            routerLinkActive="active"
            class="sb-link"
            (click)="closeMobile()"
            [title]="item.label"
          >
            <span class="sb-icon" aria-hidden="true">
              @switch (item.icon) {
                @case ('ask') {
                  <svg viewBox="0 0 16 16" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M2.75 4.25a1.5 1.5 0 0 1 1.5-1.5h7.5a1.5 1.5 0 0 1 1.5 1.5v4.5a1.5 1.5 0 0 1-1.5 1.5H6.5l-3 2.5v-2.5h-.25a1.5 1.5 0 0 1-1.5-1.5z" />
                  </svg>
                }
                @case ('search') {
                  <svg viewBox="0 0 16 16" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="7" cy="7" r="4.25" />
                    <path d="M10.5 10.5L14 14" />
                  </svg>
                }
                @case ('dashboard') {
                  <svg viewBox="0 0 16 16" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="2.25" y="2.25" width="4.75" height="4.75" rx="1" />
                    <rect x="9" y="2.25" width="4.75" height="4.75" rx="1" />
                    <rect x="2.25" y="9" width="4.75" height="4.75" rx="1" />
                    <rect x="9" y="9" width="4.75" height="4.75" rx="1" />
                  </svg>
                }
                @case ('traces') {
                  <svg viewBox="0 0 16 16" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1.5 8h3l2-4.5 3 9 2-4.5h3" />
                  </svg>
                }
                @case ('ingest') {
                  <svg viewBox="0 0 16 16" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M8 2.5v6.5M5.5 5L8 2.5 10.5 5" />
                    <path d="M2.5 10v2.5a1 1 0 0 0 1 1h9a1 1 0 0 0 1-1V10" />
                  </svg>
                }
                @case ('graph') {
                  <svg viewBox="0 0 16 16" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="3.75" cy="4" r="1.75" />
                    <circle cx="12.25" cy="4.5" r="1.75" />
                    <circle cx="7.5" cy="12" r="1.75" />
                    <path d="M5.4 4.9l5-0.5M5 5.6l1.6 4.8M10.9 6l-2.5 4.5" />
                  </svg>
                }
                @case ('admin') {
                  <svg viewBox="0 0 16 16" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M8 2l5 2v3.5c0 3-2 5.2-5 6.5-3-1.3-5-3.5-5-6.5V4z" />
                  </svg>
                }
              }
            </span>
            <span class="sb-label">{{ item.label }}</span>
          </a>
        }
      </nav>

      <!-- Recent conversations -->
      <div class="sb-recent">
        <div class="sb-recent-label sb-label">Recent</div>
        <app-chat-sidebar
          [conversations]="store.conversations()"
          [activeId]="store.activeId()"
          [loading]="store.loading()"
          (openChat)="onOpenChat($event)"
          (deleteChat)="store.delete($event)"
        />
      </div>

      <!-- Footer: user identity + sign out -->
      <div class="sb-footer">
        <div class="sb-user sb-label">
          <div class="sb-user-name">{{ userName() || userEmail() || 'Signed in' }}</div>
          @if (userEmail()) { <div class="sb-user-email">{{ userEmail() }}</div> }
        </div>
        <button class="sb-signout" type="button" (click)="signOut.emit()" title="Sign out">
          <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor"
               stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M6 2.5H3.5a1 1 0 0 0-1 1v9a1 1 0 0 0 1 1H6" />
            <path d="M10 11l3-3-3-3M13 8H6.5" />
          </svg>
          <span class="sb-label">Sign out</span>
        </button>
      </div>
    </aside>

    @if (mobileOpen()) {
      <div class="sb-backdrop" (click)="mobileOpen.set(false)"></div>
    }
  `,
  styles: [`
    :host { display: contents; }

    .sidebar {
      width: 256px;
      flex-shrink: 0;
      height: 100vh;
      background: rgba(255, 254, 251, 0.92);
      backdrop-filter: saturate(140%) blur(18px);
      -webkit-backdrop-filter: saturate(140%) blur(18px);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      min-height: 0;
      transition: width 0.2s ease;
    }
    .sidebar.collapsed { width: 60px; }

    /* Label visibility is CSS-driven so mobile can force-show regardless of the
       persisted desktop collapse flag. */
    .sidebar.collapsed .sb-label { display: none; }
    .sidebar.collapsed .sb-recent { display: none; }
    .sidebar.collapsed .sb-new { justify-content: center; }
    .sidebar.collapsed .sb-link,
    .sidebar.collapsed .sb-signout { justify-content: center; }

    /* ── Head ─────────────────────────────────────────────────── */
    .sb-head {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 12px 12px;
    }
    .sb-brand {
      flex: 1;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      text-decoration: none;
      color: var(--text);
      min-width: 0;
      &:hover { text-decoration: none; opacity: 0.8; }
    }
    .sb-logo { width: 26px; height: 26px; border-radius: 6px; object-fit: contain; flex-shrink: 0; }
    .sb-name {
      font-weight: 700;
      font-size: 1.1rem;
      letter-spacing: -0.025em;
      background: linear-gradient(135deg, var(--text) 0%, #4a4a48 100%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
      line-height: 1;
    }
    .sb-collapse {
      flex-shrink: 0;
      background: none;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      width: 28px;
      height: 28px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: var(--text-muted);
      cursor: pointer;
      &:hover { background: var(--surface-muted); color: var(--text); }
    }

    .sb-agent { position: relative; flex: 1; display: flex; align-items: center; gap: 4px; min-width: 0; }
    .sb-agent .sb-brand { flex: 1; }
    .sb-agent-toggle {
      background: none; border: none; color: var(--text-muted); cursor: pointer;
      padding: 2px; display: inline-flex; align-items: center; border-radius: 4px;
      &:hover { color: var(--text); background: var(--surface-muted); }
    }
    .sb-agent-menu {
      position: absolute; top: 100%; left: 0; z-index: 30; margin-top: 4px;
      min-width: 220px; background: var(--surface, #fff); border: 1px solid var(--border);
      border-radius: var(--radius-sm); box-shadow: 0 8px 24px rgba(0,0,0,0.12);
      padding: 4px; display: flex; flex-direction: column; gap: 2px;
    }
    .sb-agent-item {
      text-align: left; background: none; border: none; cursor: pointer;
      padding: 8px 10px; border-radius: var(--radius-sm); display: flex; flex-direction: column; gap: 2px;
      &:hover { background: var(--surface-muted); }
      &.active { background: var(--surface-muted); }
    }
    .sb-agent-item-name { font-weight: 600; font-size: 0.88rem; color: var(--text); }
    .sb-agent-item-desc { font-size: 0.75rem; color: var(--text-muted); }

    /* ── New chat ─────────────────────────────────────────────── */
    .sb-new {
      margin: 0 12px 8px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--accent);
      color: var(--text-on-accent);
      border: none;
      border-radius: var(--radius-sm);
      padding: 8px 12px;
      font-size: 0.85rem;
      font-weight: 500;
      font-family: inherit;
      cursor: pointer;
      transition: background 0.15s;
      &:hover { background: var(--accent-hover); }
    }

    /* ── Nav ──────────────────────────────────────────────────── */
    .sb-nav {
      display: flex;
      flex-direction: column;
      gap: 2px;
      padding: 4px 8px 8px;
      border-bottom: 1px solid var(--border);
    }
    .sb-link {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 10px;
      border-radius: var(--radius-sm);
      color: var(--text-muted);
      font-size: 0.88rem;
      font-weight: 500;
      text-decoration: none;
      transition: color 0.15s, background 0.15s;
      white-space: nowrap;
      &:hover { color: var(--text); background: var(--surface-muted); text-decoration: none; }
      &.active { color: var(--text); background: var(--surface-muted); }
    }
    .sb-icon { display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; width: 17px; }

    /* ── Recent ───────────────────────────────────────────────── */
    .sb-recent {
      flex: 1;
      min-height: 0;
      display: flex;
      flex-direction: column;
      padding-top: 8px;
    }
    .sb-recent-label {
      padding: 2px 16px 6px;
      font-size: 0.68rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-subtle);
    }

    /* ── Footer ───────────────────────────────────────────────── */
    .sb-footer {
      margin-top: auto;
      border-top: 1px solid var(--border);
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .sb-user { min-width: 0; padding: 2px 4px; }
    .sb-user-name {
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--text);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .sb-user-email {
      font-size: 0.72rem;
      color: var(--text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .sb-signout {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 10px;
      border-radius: var(--radius-sm);
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 0.85rem;
      font-weight: 500;
      font-family: inherit;
      cursor: pointer;
      transition: color 0.15s, background 0.15s;
      &:hover { color: var(--text); background: var(--surface-muted); }
    }

    /* ── Hamburger + backdrop (mobile only) ───────────────────── */
    .hamburger {
      display: none;
      position: fixed;
      top: 12px;
      left: 12px;
      z-index: 60;
      width: 38px;
      height: 38px;
      align-items: center;
      justify-content: center;
      background: rgba(255, 254, 251, 0.92);
      backdrop-filter: saturate(140%) blur(18px);
      -webkit-backdrop-filter: saturate(140%) blur(18px);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      color: var(--text);
      cursor: pointer;
    }
    .sb-backdrop {
      display: none;
      position: fixed;
      inset: 0;
      z-index: 199;
      background: rgba(0, 0, 0, 0.28);
    }

    @media (max-width: 720px) {
      .sidebar {
        position: fixed;
        top: 0;
        bottom: 0;
        left: 0;
        z-index: 200;
        width: 256px;
        transform: translateX(-100%);
        transition: transform 0.22s ease;
      }
      .sidebar.collapsed { width: 256px; }
      .sidebar.collapsed .sb-label { display: revert; }
      .sidebar.collapsed .sb-recent { display: flex; }
      .sidebar.mobile-open { transform: translateX(0); box-shadow: var(--shadow); }
      .sb-collapse { display: none; }
      .hamburger { display: inline-flex; }
      .sb-backdrop { display: block; }
    }
  `]
})
export class AppSidebar implements OnInit {
  private api = inject(ApiService);
  private router = inject(Router);
  store = inject(ConversationStore);
  agentSvc = inject(AgentService);
  agentMenuOpen = signal(false);

  onSelectAgent(id: string): void {
    this.agentMenuOpen.set(false);
    this.agentSvc.setActive(id);   // persists + reloads to /ask as the new agent
  }

  /** Delegated to the shell, which owns the session/auth signals. */
  signOut = output<void>();

  collapsed = signal(false);
  mobileOpen = signal(false);

  userName = signal<string>(this.api.getUserName());
  userEmail = signal<string>(this.api.getUserEmail());

  // Tab visibility per role (mirrors the backend route guards):
  //   admin     → all
  //   developer → Ask, Search, Ingest, Graph
  //   general   → Ask, Search, Graph  (+ the Recent history panel below)
  private navItems: NavItem[] = [
    { label: 'Ask', route: '/ask', icon: 'ask', roles: ['admin', 'developer', 'general'] },
    { label: 'Search', route: '/search', icon: 'search', roles: ['admin', 'developer', 'general'] },
    { label: 'Dashboard', route: '/dashboard', icon: 'dashboard', roles: ['admin'] },
    { label: 'Traces', route: '/traces', icon: 'traces', roles: ['admin'] },
    { label: 'Ingest', route: '/ingest', icon: 'ingest', roles: ['admin', 'developer'] },
    { label: 'Graph', route: '/graph', icon: 'graph', roles: ['admin', 'developer', 'general'] },
    { label: 'Admin', route: '/admin', icon: 'admin', roles: ['admin'] },
  ];

  ngOnInit(): void {
    if (localStorage.getItem(COLLAPSE_KEY) === '1') this.collapsed.set(true);
    // The sidebar is mounted once the user is signed in — populate Recent.
    this.store.refresh();
  }

  visibleNav(): NavItem[] {
    // Unknown / stale role (e.g. a pre-feature session before bootstrap
    // hydration) is treated as 'general' so Ask + Search still show.
    const role = this.api.getUserRole();
    const effective = KNOWN_ROLES.includes(role) ? role : 'general';
    return this.navItems.filter((i) => i.roles.includes(effective));
  }

  toggleCollapse(): void {
    const next = !this.collapsed();
    this.collapsed.set(next);
    try {
      localStorage.setItem(COLLAPSE_KEY, next ? '1' : '0');
    } catch {
      /* private mode */
    }
  }

  closeMobile(): void {
    this.mobileOpen.set(false);
  }

  onNewChat(): void {
    this.store.newChat();
    this.router.navigateByUrl('/ask');
    this.closeMobile();
  }

  onOpenChat(id: string): void {
    this.store.open(id);
    this.router.navigateByUrl('/ask');
    this.closeMobile();
  }
}
