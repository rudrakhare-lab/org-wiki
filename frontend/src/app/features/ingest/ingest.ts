import { Component, OnInit, signal, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, IngestPlanResponse } from '../../core/api.service';
import { inject } from '@angular/core';
import { UploadStep, UploadResult } from './upload-step';
import { PlanStep } from './plan-step';
import { ExecuteStep } from './execute-step';

import { OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';

type IngestPhase = 'upload' | 'planning' | 'plan-review' | 'executing';

// localStorage keys — persist state across tab switches
const STORAGE_JOB_ID    = 'conwo_active_ingest_job';
const STORAGE_FILENAME  = 'conwo_active_ingest_filename';
const STORAGE_UPLOAD_ID = 'conwo_active_ingest_upload_id';
const STORAGE_NOTES     = 'conwo_active_ingest_notes';
const STORAGE_SLUG      = 'conwo_active_ingest_slug';

@Component({
  selector: 'app-ingest',
  standalone: true,
  imports: [CommonModule, UploadStep, PlanStep, ExecuteStep],
  templateUrl: './ingest.html',
  styleUrl: './ingest.scss',
  encapsulation: ViewEncapsulation.None,
})
export class Ingest implements OnInit, OnDestroy {
  private api = inject(ApiService);

  phase = signal<IngestPhase>('upload');
  uploadResult = signal<UploadResult | null>(null);
  planResponse = signal<IngestPlanResponse | null>(null);
  planningError = signal('');

  private planSub?: Subscription;

  ngOnInit() {
    // Case 1: execute job already running → jump straight to execute screen
    const savedJobId = localStorage.getItem(STORAGE_JOB_ID);
    if (savedJobId) {
      const savedFilename = localStorage.getItem(STORAGE_FILENAME) ?? '';
      this.uploadResult.set({ uploadId: '', filename: savedFilename, notes: '', targetSlug: '' });
      this.planResponse.set({ session_id: '', plan: {} as any });
      this.phase.set('executing');
      return;
    }

    // Case 2: plan was in progress when user left → re-trigger the plan
    const savedUploadId = localStorage.getItem(STORAGE_UPLOAD_ID);
    if (savedUploadId) {
      const savedFilename = localStorage.getItem(STORAGE_FILENAME) ?? '';
      const savedNotes    = localStorage.getItem(STORAGE_NOTES)    ?? '';
      const savedSlug     = localStorage.getItem(STORAGE_SLUG)     ?? '';
      this.uploadResult.set({ uploadId: savedUploadId, filename: savedFilename, notes: savedNotes, targetSlug: savedSlug });
      this.phase.set('planning');
      this._runPlan(savedUploadId, savedNotes, savedSlug);
    }
  }

  ngOnDestroy() {
    this.planSub?.unsubscribe();
  }

  onUploaded(result: UploadResult) {
    this.uploadResult.set(result);
    this.phase.set('planning');
    this.planningError.set('');

    // Persist upload state so returning to this tab can re-trigger planning
    localStorage.setItem(STORAGE_UPLOAD_ID, result.uploadId);
    localStorage.setItem(STORAGE_FILENAME,  result.filename);
    localStorage.setItem(STORAGE_NOTES,     result.notes);
    localStorage.setItem(STORAGE_SLUG,      result.targetSlug);

    this._runPlan(result.uploadId, result.notes, result.targetSlug);
  }

  private _runPlan(uploadId: string, notes: string, targetSlug: string) {
    this.planSub?.unsubscribe();
    this.planSub = this.api.planIngest(uploadId, notes, targetSlug).subscribe({
      next: (resp) => {
        localStorage.removeItem(STORAGE_UPLOAD_ID);  // plan done, no need to re-trigger
        this.planResponse.set(resp);
        this.phase.set('plan-review');
      },
      error: (err: { error?: { detail?: string } }) => {
        localStorage.removeItem(STORAGE_UPLOAD_ID);
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
    localStorage.removeItem(STORAGE_UPLOAD_ID);
    localStorage.removeItem(STORAGE_NOTES);
    localStorage.removeItem(STORAGE_SLUG);
    this.phase.set('upload');
    this.uploadResult.set(null);
    this.planResponse.set(null);
    this.planningError.set('');
  }
}
