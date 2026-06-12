import { Component, inject, signal } from '@angular/core';
import { RouterOutlet, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { ApiService } from './core/api.service';
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
  readonly title = 'Conwo';
  private router = inject(Router);
  private api = inject(ApiService);
  private conversations = inject(ConversationStore);

  currentUrl = signal<string>(this.router.url);
  signedIn = signal<boolean>(this.readToken().length > 0);

  constructor() {
    this.router.events
      .pipe(filter(e => e instanceof NavigationEnd))
      .subscribe(e => {
        this.currentUrl.set((e as NavigationEnd).urlAfterRedirects);
        this.signedIn.set(this.readToken().length > 0);
      });
  }

  showHeaderNav(): boolean {
    return !this.currentUrl().startsWith('/login') && this.signedIn();
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
