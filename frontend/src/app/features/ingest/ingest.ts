import { Component, OnInit, signal, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, IngestPlanResponse } from '../../core/api.service';
import { inject } from '@angular/core';
import { UploadStep, UploadResult } from './upload-step';
import { PlanStep } from './plan-step';
import { ExecuteStep } from './execute-step';

type IngestPhase = 'upload' | 'planning' | 'plan-review' | 'executing';

const STORAGE_JOB_ID  = 'conwo_active_ingest_job';
const STORAGE_FILENAME = 'conwo_active_ingest_filename';

@Component({
  selector: 'app-ingest',
  standalone: true,
  imports: [CommonModule, UploadStep, PlanStep, ExecuteStep],
  templateUrl: './ingest.html',
  styleUrl: './ingest.scss',
  encapsulation: ViewEncapsulation.None,
})
export class Ingest implements OnInit {
  private api = inject(ApiService);

  phase = signal<IngestPhase>('upload');
  uploadResult = signal<UploadResult | null>(null);
  planResponse = signal<IngestPlanResponse | null>(null);
  planningError = signal('');

  ngOnInit() {
    // If there's an active job from a previous visit, resume showing it
    const savedJobId = localStorage.getItem(STORAGE_JOB_ID);
    const savedFilename = localStorage.getItem(STORAGE_FILENAME) ?? '';
    if (savedJobId) {
      this.uploadResult.set({ uploadId: '', filename: savedFilename, notes: '', targetSlug: '' });
      // planResponse session_id is not needed for resume — execute-step reads the jobId from localStorage
      this.planResponse.set({ session_id: '', plan: {} as any });
      this.phase.set('executing');
    }
  }

  onUploaded(result: UploadResult) {
    this.uploadResult.set(result);
    this.phase.set('planning');
    this.planningError.set('');

    this.api.planIngest(result.uploadId, result.notes, result.targetSlug).subscribe({
      next: (resp) => {
        this.planResponse.set(resp);
        this.phase.set('plan-review');
      },
      error: (err: { error?: { detail?: string } }) => {
        this.planningError.set(err?.error?.detail ?? 'Planning failed. Try again.');
        this.phase.set('upload');
      },
    });
  }

  onApprove() {
    this.phase.set('executing');
  }

  onCancel() {
    this.reset();
  }

  onIngestAnother() {
    this.reset();
  }

  private reset() {
    localStorage.removeItem(STORAGE_JOB_ID);
    localStorage.removeItem(STORAGE_FILENAME);
    this.phase.set('upload');
    this.uploadResult.set(null);
    this.planResponse.set(null);
    this.planningError.set('');
  }
}
