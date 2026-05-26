import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { ApiService } from '../../core/api.service';

const API_BASE = 'http://localhost:8000';

@Component({
  selector: 'app-login',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="login-shell">
      <div class="login-card">
        <h1 class="login-title">Sign in</h1>
        <p class="login-sub">Enter your access token to use Conwo.</p>

        <form class="login-form" (submit)="onSubmit($event)">
          <label class="login-field">
            <span class="login-label">Access token</span>
            <input
              type="password"
              [(ngModel)]="token"
              name="token"
              autocomplete="off"
              placeholder="32-char hex token"
              class="login-input"
              [disabled]="busy()"
              autofocus
              aria-label="Access token"
            />
          </label>

          <button
            type="submit"
            class="login-btn"
            [disabled]="busy() || !token.trim()">
            {{ busy() ? 'Signing in…' : 'Sign in' }}
          </button>

          @if (error()) {
            <div class="login-error" role="alert">{{ error() }}</div>
          }
        </form>

        <p class="login-hint">Don't have a token? Contact your admin.</p>
      </div>
    </div>
  `,
  styles: [`
    .login-shell {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 70vh;
      padding: 24px;
    }
    .login-card {
      width: 100%;
      max-width: 380px;
      padding: 32px 28px;
      background: var(--bg-elevated, var(--bg));
      border: 1px solid var(--border);
      border-radius: 12px;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04);
    }
    .login-title { margin: 0 0 6px; font-size: 1.4rem; }
    .login-sub { margin: 0 0 22px; color: var(--text-muted); font-size: 0.9rem; }
    .login-form { display: flex; flex-direction: column; gap: 14px; }
    .login-field { display: flex; flex-direction: column; gap: 6px; }
    .login-label {
      font-size: 0.78rem; text-transform: uppercase;
      letter-spacing: 0.04em; color: var(--text-muted);
    }
    .login-input {
      padding: 10px 12px;
      font-size: 0.92rem;
      font-family: var(--font-mono, monospace);
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--bg);
      color: var(--text);

      &:focus { outline: none; border-color: var(--info); }
      &:disabled { opacity: 0.6; cursor: not-allowed; }
    }
    .login-btn {
      padding: 10px 16px;
      background: var(--accent, rgb(59, 130, 246));
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 0.92rem;
      font-weight: 500;
      cursor: pointer;

      &:hover:not(:disabled) { filter: brightness(1.05); }
      &:disabled { opacity: 0.5; cursor: not-allowed; }
    }
    .login-error {
      padding: 8px 12px;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: var(--error, rgb(180, 50, 50));
      border-radius: 6px;
      font-size: 0.85rem;
    }
    .login-hint {
      margin: 22px 0 0;
      font-size: 0.82rem;
      color: var(--text-muted);
      text-align: center;
    }
  `]
})
export class Login {
  private api = inject(ApiService);
  private router = inject(Router);
  private http = inject(HttpClient);

  token = '';
  busy = signal(false);
  error = signal('');

  onSubmit(ev: Event) {
    ev.preventDefault();
    const t = this.token.trim();
    if (!t) return;
    this.busy.set(true);
    this.error.set('');
    // Validate the token by hitting /status with Authorization. The interceptor
    // would normally attach the stored token, but we want to validate the NEW
    // one before persisting it — so attach it manually here and bypass storage.
    const headers = new HttpHeaders({ Authorization: `Bearer ${t}` });
    this.http.get(`${API_BASE}/status`, { headers }).subscribe({
      next: () => {
        this.api.setAdminToken(t);
        this.busy.set(false);
        this.router.navigateByUrl('/ask');
      },
      error: err => {
        this.busy.set(false);
        if (err?.status === 401) {
          this.error.set('Access denied — check your token or contact your admin.');
        } else {
          this.error.set(`Could not reach the server (${err?.status ?? 'network error'}).`);
        }
      },
    });
  }
}
