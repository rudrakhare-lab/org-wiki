import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, Agent } from '../../core/api.service';
import { AgentService } from '../../core/agent.service';

const PROTECTED = new Set(['conwo', 'infosec']);

@Component({
  selector: 'app-manage-agents',
  standalone: true,
  imports: [FormsModule],
  styleUrl: './manage-agents.scss',
  template: `
    <section class="manage-agents">
      <h1>Agents</h1>

      <div class="create-card">
        <h2>Create a new agent</h2>
        <p class="hint">Name it and say in one line what it does. It starts with an empty knowledge
          base — ingest documents to teach it. It gets its own dashboard, traces, ingest, and graph.</p>
        <div class="form">
          <input [(ngModel)]="newName" placeholder="Name, e.g. Legal" [disabled]="busy()" />
          <input [(ngModel)]="newDesc" placeholder="One line: what this agent does" [disabled]="busy()"
                 (keyup.enter)="create()" />
          <button class="primary" (click)="create()" [disabled]="busy() || !newName().trim()">
            {{ busy() ? 'Creating…' : 'Create Agent' }}
          </button>
        </div>
        @if (error()) { <p class="error">{{ error() }}</p> }
        @if (created(); as c) {
          <div class="created">
            <span class="dot" [style.background]="c.accent || '#1e293b'"></span>
            Created <strong>{{ c.display_name }}</strong> — now selectable in the switcher.
          </div>
        }
      </div>

      <h2>Existing agents</h2>
      <div class="agent-grid">
        @for (a of agents(); track a.id) {
          <div class="agent-card" [style.--card-accent]="a.accent || '#64748b'">
            @if (editing() === a.id) {
              <input class="edit-name" [(ngModel)]="editName" placeholder="Name" />
              <input class="edit-desc" [(ngModel)]="editDesc" placeholder="Description" />
              <div class="actions">
                <button class="primary" (click)="saveRename(a)">Save</button>
                <button class="ghost" (click)="editing.set(null)">Cancel</button>
              </div>
            } @else {
              <div class="card-head">
                <span class="dot" [style.background]="a.accent || '#64748b'"></span>
                <span class="title">{{ a.display_name }}</span>
                @if (isProtected(a.id)) { <span class="badge">built-in</span> }
              </div>
              <p class="desc">{{ a.description || '—' }}</p>
              <code class="id">{{ a.id }}</code>
              <div class="actions">
                <button class="ghost" (click)="startRename(a)">Rename</button>
                @if (!isProtected(a.id)) {
                  <button class="ghost" (click)="archive(a)">Archive</button>
                  @if (deletingId() === a.id) {
                    <span class="confirm">
                      <input [(ngModel)]="deleteText" [placeholder]="'type ' + a.id" />
                      <button class="danger" [disabled]="deleteText !== a.id" (click)="confirmDelete(a)">Delete</button>
                      <button class="ghost" (click)="deletingId.set(null)">Cancel</button>
                    </span>
                  } @else {
                    <button class="danger" (click)="startDelete(a)">Delete</button>
                  }
                }
              </div>
            }
          </div>
        }
      </div>

      <section class="access-requests">
        <h2>Agent access requests</h2>
        @if (accessRequests().length === 0) {
          <div class="empty">No pending requests.</div>
        } @else {
          <table>
            <thead><tr><th>User</th><th>Agent</th><th>Requested</th><th>Action</th></tr></thead>
            <tbody>
              @for (r of accessRequests(); track r.user_email + r.agent_id) {
                <tr>
                  <td>{{ r.user_email }}</td><td>{{ r.agent_id }}</td><td>{{ r.requested_at }}</td>
                  <td>
                    <button (click)="approve(r.user_email, r.agent_id)">Approve</button>
                    <button (click)="reject(r.user_email, r.agent_id)">Reject</button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        }
      </section>

      <section class="grants">
        <h2>Agent grants</h2>
        <div class="grant-form">
          <input placeholder="user email" [ngModel]="grantEmail()" (ngModelChange)="grantEmail.set($event)" />
          <input placeholder="agent id" [ngModel]="grantAgentId()" (ngModelChange)="grantAgentId.set($event)" />
          <button (click)="grantDirect()">Grant</button>
        </div>
        @if (grants().length === 0) {
          <div class="empty">No grants yet.</div>
        } @else {
          <table>
            <thead><tr><th>User</th><th>Agent</th><th>By</th><th></th></tr></thead>
            <tbody>
              @for (g of grants(); track g.user_email + g.agent_id) {
                <tr>
                  <td>{{ g.user_email }}</td><td>{{ g.agent_id }}</td><td>{{ g.decided_by }}</td>
                  <td><button (click)="revoke(g.user_email, g.agent_id)">Revoke</button></td>
                </tr>
              }
            </tbody>
          </table>
        }
      </section>
    </section>
  `,
})
export class ManageAgents {
  private api = inject(ApiService);
  private agentSvc = inject(AgentService);

  agents = this.agentSvc.agents;
  newName = signal('');
  newDesc = signal('');
  busy = signal(false);
  error = signal('');
  created = signal<Agent | null>(null);
  editing = signal<string | null>(null);
  editName = '';
  editDesc = '';
  deletingId = signal<string | null>(null);
  deleteText = '';
  accessRequests = signal<{ user_email: string; agent_id: string; requested_at: string }[]>([]);
  grants = signal<{ user_email: string; agent_id: string; decided_by: string }[]>([]);
  grantEmail = signal('');
  grantAgentId = signal('');

  constructor() { this.agentSvc.loadAgents(); this.loadAccess(); }

  isProtected(id: string): boolean { return PROTECTED.has(id); }

  loadAccess() {
    this.api.getAgentAccessRequests().subscribe({ next: r => this.accessRequests.set(r), error: () => {} });
    this.api.getAgentGrants().subscribe({ next: g => this.grants.set(g), error: () => {} });
  }
  approve(e: string, id: string) { this.api.approveAgentAccess(e, id).subscribe({ next: () => this.loadAccess() }); }
  reject(e: string, id: string) { this.api.rejectAgentAccess(e, id).subscribe({ next: () => this.loadAccess() }); }
  revoke(e: string, id: string) { this.api.revokeAgentAccess(e, id).subscribe({ next: () => this.loadAccess() }); }
  grantDirect() {
    const e = this.grantEmail().trim(), id = this.grantAgentId().trim();
    if (!e || !id) return;
    this.api.grantAgentAccess(e, id).subscribe({ next: () => { this.grantEmail.set(''); this.loadAccess(); } });
  }

  create(): void {
    const name = this.newName().trim();
    if (!name || this.busy()) return;
    this.busy.set(true); this.error.set(''); this.created.set(null);
    this.api.createAgent(name, this.newDesc().trim()).subscribe({
      next: (agent) => {
        this.busy.set(false); this.created.set(agent);
        this.newName.set(''); this.newDesc.set('');
        this.agentSvc.loadAgents();
      },
      error: (err) => {
        this.busy.set(false);
        this.error.set(err?.error?.detail || 'Could not create agent. It may already exist.');
      },
    });
  }

  startRename(a: Agent): void { this.editing.set(a.id); this.editName = a.display_name; this.editDesc = a.description || ''; }

  saveRename(a: Agent): void {
    const name = this.editName.trim();
    if (!name) return;
    this.api.updateAgent(a.id, { display_name: name, description: this.editDesc.trim() }).subscribe({
      next: () => { this.editing.set(null); this.agentSvc.loadAgents(); },
      error: () => this.error.set('Update failed.'),
    });
  }

  archive(a: Agent): void {
    if (!confirm(`Archive "${a.display_name}"? It will disappear from the switcher.`)) return;
    this.api.archiveAgent(a.id).subscribe({
      next: () => this.agentSvc.loadAgents(),
      error: (err) => this.error.set(err?.error?.detail || 'Archive failed.'),
    });
  }

  startDelete(a: Agent): void { this.deletingId.set(a.id); this.deleteText = ''; }

  confirmDelete(a: Agent): void {
    if (this.deleteText !== a.id) return;
    this.api.deleteAgent(a.id).subscribe({
      next: () => { this.deletingId.set(null); this.agentSvc.loadAgents(); },
      error: (err) => this.error.set(err?.error?.detail || 'Delete failed.'),
    });
  }
}
