import { AfterViewInit, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { ApiService } from '../../core/api.service';

declare const google: any;

const API_BASE = '';
// Fill this in from Google Cloud Console → APIs & Services → Credentials
// It ends in .apps.googleusercontent.com
const GOOGLE_CLIENT_ID = '394997129475-vptjprrehufpvhnlh3tad78uqk69u54h.apps.googleusercontent.com';

@Component({
  selector: 'app-login',
  imports: [CommonModule],
  template: `
    <div class="login-page">
      <div class="login-brand" aria-label="Conwo">
        <img src="logo.png" alt="" class="login-logo" />
        <span class="login-wordmark">Conwo</span>
      </div>

      <div class="login-center">
        <div class="login-card">
          <h1 class="login-title">Welcome to Conwo</h1>
          <p class="login-sub">Your workplace knowledge, instantly answered.</p>

          <div class="signin-btn-wrap">
            <div id="google-signin-btn"></div>
          </div>

          @if (error()) {
            <div class="login-error" role="alert">{{ error() }}</div>
          }

          @if (busy()) {
            <div class="login-busy">Signing in…</div>
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; flex: 1; min-width: 0; }

    .login-page {
      position: relative;
      min-height: 100vh;
      width: 100%;
      display: flex;
      flex-direction: column;
    }

    .login-brand {
      position: absolute;
      top: 24px;
      left: 28px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .login-logo {
      width: 28px;
      height: 28px;
      border-radius: 6px;
      object-fit: contain;
    }
    .login-wordmark {
      font-weight: 700;
      font-size: 1.2rem;
      letter-spacing: -0.025em;
      background: linear-gradient(135deg, var(--text) 0%, #4a4a48 100%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
      line-height: 1;
    }

    .login-center {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }

    .login-card {
      width: 100%;
      max-width: 400px;
      padding: 40px 32px;
      background: var(--surface, #ffffff);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg, 16px);
      box-shadow: var(--shadow, 0 4px 24px rgba(0, 0, 0, 0.06));
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      text-align: center;
    }
    .login-title {
      margin: 0;
      font-size: 1.6rem;
      font-weight: 600;
      letter-spacing: -0.02em;
      color: var(--text);
    }
    .login-sub {
      margin: 0 0 14px;
      color: var(--text-muted);
      font-size: 0.95rem;
    }
    .signin-btn-wrap { margin: 6px 0; min-height: 44px; }
    .login-error {
      width: 100%;
      padding: 8px 12px;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: var(--error, rgb(180, 50, 50));
      border-radius: 6px;
      font-size: 0.85rem;
      text-align: center;
    }
    .login-busy {
      color: var(--text-muted);
      font-size: 0.9rem;
    }
  `]
})
export class Login implements AfterViewInit {
  private api = inject(ApiService);
  private router = inject(Router);
  private http = inject(HttpClient);

  busy = signal(false);
  error = signal('');

  ngAfterViewInit() {
    if (!GOOGLE_CLIENT_ID) {
      this.error.set('Server configuration error: GOOGLE_CLIENT_ID is not set.');
      return;
    }
    google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: (response: any) => this.handleCredential(response),
    });
    google.accounts.id.renderButton(
      document.getElementById('google-signin-btn')!,
      { theme: 'outline', size: 'large', width: 320 }
    );
  }

  private handleCredential(response: any) {
    this.busy.set(true);
    this.error.set('');
    const headers = new HttpHeaders({ 'Content-Type': 'application/json' });
    this.http.post<{ token: string; email: string; name: string; role: string }>(
      `${API_BASE}/auth/google`,
      { credential: response.credential },
      { headers }
    ).subscribe({
      next: (res) => {
        this.api.setAdminToken(res.token);
        this.api.setUserInfo(res.email, res.name, res.role);
        this.busy.set(false);
        this.router.navigateByUrl('/ask');
      },
      error: (err) => {
        this.busy.set(false);
        if (err?.status === 403) {
          this.error.set('Access denied — only @moveinsync.com accounts are allowed.');
        } else if (err?.status === 500) {
          this.error.set('Server configuration error. Contact the admin.');
        } else {
          this.error.set(`Could not reach the server (${err?.status ?? 'network error'}).`);
        }
      },
    });
  }
}
