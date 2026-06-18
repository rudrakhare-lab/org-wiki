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

  constructor() { this.agentSvc.loadAgents(); }

  isProtected(id: string): boolean { return PROTECTED.has(id); }

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
