import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';

const ADMIN_TOKEN_KEY = 'conwo_admin_token';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  readonly title = 'Conwo';
  private router = inject(Router);

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
