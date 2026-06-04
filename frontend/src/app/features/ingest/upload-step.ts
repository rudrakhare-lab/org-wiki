import { Component, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';
import { inject } from '@angular/core';

export interface UploadResult {
  uploadId: string;
  filename: string;
  notes: string;
  targetSlug: string;
}

@Component({
  selector: 'app-upload-step',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="upload-step">
      <h2>Ingest Document</h2>
      <p class="subtitle">Upload a document to add it to the wiki.</p>

      <div
        class="drop-zone"
        [class.drag-over]="dragOver()"
        [class.has-file]="selectedFile()"
        (dragover)="onDragOver($event)"
        (dragleave)="dragOver.set(false)"
        (drop)="onDrop($event)"
        (click)="fileInput.click()"
      >
        @if (selectedFile(); as f) {
          <div class="file-info">
            <span class="file-icon">📄</span>
            <span class="file-name">{{ f.name }}</span>
            <span class="file-size">{{ formatSize(f.size) }}</span>
          </div>
        } @else {
          <div class="drop-hint">
            <span class="drop-icon">📄</span>
            <span>Drop a file here, or click to browse</span>
            <span class="drop-types">PDF · DOCX · XLSX · MD · TXT</span>
          </div>
        }
        <input
          #fileInput
          type="file"
          style="display:none"
          accept=".pdf,.docx,.doc,.xlsx,.xls,.md,.txt,.rtf"
          (change)="onFileSelected($event)"
        />
      </div>

      @if (typeError()) {
        <div class="error-msg">{{ typeError() }}</div>
      }

      <div class="form-field">
        <label>Context for the AI <span class="optional">(optional)</span></label>
        <textarea
          [(ngModel)]="notes"
          placeholder="e.g. Updated VMS PRD from Q3 planning, supersedes the earlier version"
          rows="3"
        ></textarea>
      </div>

      <div class="form-field">
        <label>Target module <span class="optional">(optional — AI will detect if blank)</span></label>
        <input
          type="text"
          [(ngModel)]="targetSlug"
          placeholder="e.g. visitor-management"
          list="module-slugs"
        />
        <datalist id="module-slugs">
          @for (slug of knownSlugs; track slug) {
            <option [value]="slug"></option>
          }
        </datalist>
      </div>

      @if (error()) {
        <div class="error-msg">{{ error() }}</div>
      }

      <button
        class="btn-primary"
        [disabled]="!selectedFile() || loading()"
        (click)="submit()"
      >
        @if (loading()) { Uploading… } @else { Upload & Analyse → }
      </button>
    </div>
  `,
})
export class UploadStep {
  private api = inject(ApiService);

  done = output<UploadResult>();

  selectedFile = signal<File | null>(null);
  dragOver = signal(false);
  loading = signal(false);
  error = signal('');
  typeError = signal('');
  notes = '';
  targetSlug = '';

  readonly knownSlugs = [
    'access-management', 'admin-experience', 'create-employee-form', 'delegation',
    'desk-management', 'digital-wayfinding', 'employee-experience', 'employee-provisioning',
    'esg-dashboard', 'floor-kiosk', 'guard-app-kiosks', 'implementation',
    'meal-management', 'meeting-rooms', 'mobile-app', 'ms-teams-integration',
    'parking-management', 'safe-reach', 'sso', 'tags-desk-parking', 'third-party',
    'visitor-management',
  ];

  private readonly supported = new Set(['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.md', '.txt', '.rtf']);

  onDragOver(e: DragEvent) {
    e.preventDefault();
    this.dragOver.set(true);
  }

  onDrop(e: DragEvent) {
    e.preventDefault();
    this.dragOver.set(false);
    const f = e.dataTransfer?.files?.[0];
    if (f) this.setFile(f);
  }

  onFileSelected(e: Event) {
    const f = (e.target as HTMLInputElement).files?.[0];
    if (f) this.setFile(f);
  }

  private setFile(f: File) {
    const ext = '.' + f.name.split('.').pop()!.toLowerCase();
    if (!this.supported.has(ext)) {
      this.typeError.set(`Unsupported file type: ${ext}. Allowed: PDF, DOCX, XLSX, MD, TXT`);
      this.selectedFile.set(null);
      return;
    }
    this.typeError.set('');
    this.selectedFile.set(f);
  }

  formatSize(bytes: number): string {
    return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${(bytes / 1024).toFixed(0)} KB`;
  }

  submit() {
    const f = this.selectedFile();
    if (!f) return;
    this.loading.set(true);
    this.error.set('');

    this.api.uploadIngestFile(f, this.notes, this.targetSlug).subscribe({
      next: (upload) => {
        this.loading.set(false);
        this.done.emit({
          uploadId: upload.upload_id,
          filename: upload.filename ?? f.name,
          notes: this.notes,
          targetSlug: this.targetSlug,
        });
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err?.error?.detail ?? 'Upload failed. Try again.');
      },
    });
  }
}
