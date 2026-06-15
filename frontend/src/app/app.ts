import { Component, inject, signal } from '@angular/core';
import { RouterOutlet, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { ApiService } from './core/api.service';
import { AgentService } from './core/agent.service';
import { ConversationStore } from './core/conversation.store';
import { AppSidebar } from './shared/app-sidebar/app-sidebar';

const ADMIN_TOKEN_KEY = 'conwo_admin_token';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, AppSidebar],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  get title(): string { return this.agentSvc.activeName(); }
  private router = inject(Router);
  private api = inject(ApiService);
  private conversations = inject(ConversationStore);
  private agentSvc = inject(AgentService);

  currentUrl = signal<string>(this.router.url);
  signedIn = signal<boolean>(this.readToken().length > 0);

  constructor() {
    this.router.events
      .pipe(filter(e => e instanceof NavigationEnd))
      .subscribe(e => {
        this.currentUrl.set((e as NavigationEnd).urlAfterRedirects);
        this.signedIn.set(this.readToken().length > 0);
      });
    this.hydrateUser();
    if (this.signedIn()) {
      this.agentSvc.loadAgents();
    }
  }

  /**
   * On bootstrap, refresh the signed-in user's role + approval from the server.
   * This (a) gives pre-feature sessions their role/approved flags, (b) picks up
   * an admin approval without a re-login, and (c) propagates role changes. A 401
   * means the stored token is invalid → sign out. (Deep-linking before this
   * resolves falls back to the optimistic localStorage flags — acceptable for the
   * pilot; the backend is the real gate.)
   */
  private hydrateUser() {
    if (!this.signedIn()) return;
    this.api.getMe().subscribe({
      next: (me) => {
        this.api.setUserRole(me.role);
        this.api.setUserApproved(me.approved);
        this.agentSvc.loadAgents();
        const url = this.currentUrl();
        if (!me.approved && !url.startsWith('/pending') && !url.startsWith('/login')) {
          this.router.navigateByUrl('/pending');
        }
      },
      error: (err) => {
        if (err?.status === 401) this.signOut();
      },
    });
  }

  showHeaderNav(): boolean {
    const url = this.currentUrl();
    return !url.startsWith('/login') && !url.startsWith('/pending') && this.signedIn();
  }

  signOut() {
    try {
      localStorage.removeItem(ADMIN_TOKEN_KEY);
    } catch { /* private mode */ }
    this.api.clearUserInfo();
    this.conversations.reset();
    this.signedIn.set(false);
    this.router.navigateByUrl('/login');
  }

  private readToken(): string {
    try {
      return localStorage.getItem(ADMIN_TOKEN_KEY) ?? '';
    } catch {
      return '';
    }
  }
}
