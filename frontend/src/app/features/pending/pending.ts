import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { ApiService } from '../../core/api.service';

/**
 * Pending-approval screen. Shown (via authGuard → /pending) to a signed-in user
 * whose account an admin has not yet approved. No app sidebar (the shell hides it
 * on /pending). "Check again" re-fetches /auth/me and proceeds to /ask once
 * approved — no re-login needed.
 */
@Component({
  selector: 'app-pending',
  template: `
    <div class="pending-page">
      <div class="pending-brand" aria-label="Conwo">
        <img src="logo.png" alt="" class="pending-logo" />
        <span class="pending-wordmark">Conwo</span>
      </div>

      <div class="pending-center">
        <div class="pending-card">
          <div class="pending-icon" aria-hidden="true">⏳</div>
          <h1 class="pending-title">Your account is pending approval</h1>
          <p class="pending-sub">
            Thanks for signing in@if (email()) {, <strong>{{ email() }}</strong>}. An administrator
            needs to approve your access before you can start asking questions.
            You’ll be able to use Conwo as soon as they do.
          </p>

          <div class="pending-actions">
            <button class="pending-btn primary" type="button" (click)="checkAgain()" [disabled]="checking()">
              {{ checking() ? 'Checking…' : 'Check again' }}
            </button>
            <button class="pending-btn ghost" type="button" (click)="signOut()">Sign out</button>
          </div>

          @if (message()) {
            <div class="pending-msg">{{ message() }}</div>
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; flex: 1; min-width: 0; }

    .pending-page {
      position: relative;
      min-height: 100vh;
      width: 100%;
      display: flex;
      flex-direction: column;
    }
    .pending-brand {
      position: absolute;
      top: 24px;
      left: 28px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .pending-logo { width: 28px; height: 28px; border-radius: 6px; object-fit: contain; }
    .pending-wordmark {
      font-weight: 700;
      font-size: 1.2rem;
      letter-spacing: -0.025em;
      background: linear-gradient(135deg, var(--text) 0%, #4a4a48 100%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
      line-height: 1;
    }
    .pending-center {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }
    .pending-card {
      width: 100%;
      max-width: 440px;
      padding: 40px 32px;
      background: var(--surface, #ffffff);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg, 16px);
      box-shadow: var(--shadow, 0 4px 24px rgba(0, 0, 0, 0.06));
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
      text-align: center;
    }
    .pending-icon { font-size: 2rem; line-height: 1; }
    .pending-title {
      margin: 0;
      font-size: 1.4rem;
      font-weight: 600;
      letter-spacing: -0.02em;
      color: var(--text);
    }
    .pending-sub {
      margin: 0 0 8px;
      color: var(--text-muted);
      font-size: 0.95rem;
      line-height: 1.5;
    }
    .pending-actions { display: flex; gap: 10px; margin-top: 4px; }
    .pending-btn {
      border-radius: var(--radius-sm);
      padding: 9px 18px;
      font-size: 0.9rem;
      font-weight: 500;
      font-family: inherit;
      cursor: pointer;
      transition: background 0.15s, color 0.15s, opacity 0.15s;
    }
    .pending-btn.primary {
      background: var(--accent);
      color: var(--text-on-accent);
      border: none;
      &:hover { background: var(--accent-hover); }
      &:disabled { opacity: 0.6; cursor: default; }
    }
    .pending-btn.ghost {
      background: none;
      border: 1px solid var(--border);
      color: var(--text-muted);
      &:hover { color: var(--text); background: var(--surface-muted); }
    }
    .pending-msg {
      margin-top: 6px;
      color: var(--text-muted);
      font-size: 0.85rem;
    }
  `]
})
export class Pending {
  private api = inject(ApiService);
  private router = inject(Router);

  checking = signal(false);
  message = signal('');
  email = signal<string>(this.api.getUserEmail());

  checkAgain() {
    this.checking.set(true);
    this.message.set('');
    this.api.getMe().subscribe({
      next: (me) => {
        this.checking.set(false);
        this.api.setUserRole(me.role);
        this.api.setUserApproved(me.approved);
        if (me.approved) {
          this.router.navigateByUrl('/ask');
        } else {
          this.message.set('Still pending — your account hasn’t been approved yet.');
        }
      },
      error: () => {
        this.checking.set(false);
        this.message.set('Couldn’t check your status just now. Please try again in a moment.');
      },
    });
  }

  signOut() {
    try { localStorage.removeItem('conwo_admin_token'); } catch { /* private mode */ }
    this.api.clearUserInfo();
    this.router.navigateByUrl('/login');
  }
}
