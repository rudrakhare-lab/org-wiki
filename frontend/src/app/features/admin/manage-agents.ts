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
        <p class="hint">Type a name. The agent starts with an empty knowledge base — ingest
          documents to teach it. It gets its own dashboard, traces, ingest, and graph automatically.</p>
        <div class="row">
          <input [(ngModel)]="newName" placeholder="e.g. Legal" (keyup.enter)="create()" [disabled]="busy()" />
          <button class="primary" (click)="create()" [disabled]="busy() || !newName().trim()">
            {{ busy() ? 'Creating…' : 'Create Agent' }}
          </button>
        </div>
        @if (error()) { <p class="error">{{ error() }}</p> }
        @if (created(); as c) {
          <div class="created">
            <span class="dot" [style.background]="c.accent || '#1e293b'"></span>
            Created <strong>{{ c.display_name }}</strong> — now selectable in the switcher.
            <div class="identity">Identity: <em>{{ c.identity || c.description }}</em></div>
          </div>
        }
      </div>

      <h2>Existing agents</h2>
      <table class="agents">
        <thead><tr><th></th><th>Name</th><th>ID</th><th>Theme</th><th></th></tr></thead>
        <tbody>
          @for (a of agents(); track a.id) {
            <tr>
              <td><span class="dot" [style.background]="a.accent || '#1e293b'"></span></td>
              <td>
                @if (editing() === a.id) {
                  <input [(ngModel)]="editName" />
                } @else { {{ a.display_name }} }
              </td>
              <td class="mono">{{ a.id }}</td>
              <td>{{ a.theme_base || (a.id === 'conwo' ? 'light' : 'dark') }}</td>
              <td class="actions">
                @if (editing() === a.id) {
                  <button (click)="saveRename(a)">Save</button>
                  <button (click)="editing.set(null)">Cancel</button>
                } @else {
                  <button (click)="startRename(a)">Rename</button>
                  @if (!isProtected(a.id)) {
                    <button class="danger" (click)="archive(a)">Archive</button>
                  } @else { <span class="protected">built-in</span> }
                }
              </td>
            </tr>
          }
        </tbody>
      </table>
    </section>
  `,
})
export class ManageAgents {
  private api = inject(ApiService);
  private agentSvc = inject(AgentService);

  agents = this.agentSvc.agents;
  newName = signal('');
  busy = signal(false);
  error = signal('');
  created = signal<Agent | null>(null);
  editing = signal<string | null>(null);
  editName = '';

  constructor() { this.agentSvc.loadAgents(); }

  isProtected(id: string): boolean { return PROTECTED.has(id); }

  create(): void {
    const name = this.newName().trim();
    if (!name || this.busy()) return;
    this.busy.set(true); this.error.set(''); this.created.set(null);
    this.api.createAgent(name).subscribe({
      next: (agent) => {
        this.busy.set(false);
        this.created.set(agent);
        this.newName.set('');
        this.agentSvc.loadAgents(); // refresh switcher list
      },
      error: (err) => {
        this.busy.set(false);
        this.error.set(err?.error?.detail || 'Could not create agent. It may already exist.');
      },
    });
  }

  startRename(a: Agent): void { this.editing.set(a.id); this.editName = a.display_name; }

  saveRename(a: Agent): void {
    const name = this.editName.trim();
    if (!name) return;
    this.api.updateAgent(a.id, { display_name: name }).subscribe({
      next: () => { this.editing.set(null); this.agentSvc.loadAgents(); },
      error: () => this.error.set('Rename failed.'),
    });
  }

  archive(a: Agent): void {
    if (!confirm(`Archive "${a.display_name}"? It will disappear from the switcher.`)) return;
    this.api.archiveAgent(a.id).subscribe({
      next: () => this.agentSvc.loadAgents(),
      error: (err) => this.error.set(err?.error?.detail || 'Archive failed.'),
    });
  }
}
