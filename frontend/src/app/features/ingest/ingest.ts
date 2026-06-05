import { Component, OnInit, OnDestroy, signal, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, IngestPlanResponse } from '../../core/api.service';
import { inject } from '@angular/core';
import { UploadStep, UploadResult } from './upload-step';
import { PlanStep } from './plan-step';
import { ExecuteStep } from './execute-step';
import { Subscription } from 'rxjs';

type IngestPhase = 'upload' | 'planning' | 'plan-review' | 'executing';

// localStorage keys — persist state across tab switches
const STORAGE_JOB_ID      = 'conwo_active_ingest_job';
const STORAGE_FILENAME    = 'conwo_active_ingest_filename';
const STORAGE_PLAN_JOB_ID = 'conwo_active_ingest_plan_job';

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

  private planStartSub?: Subscription;
  private planPollHandle?: ReturnType<typeof setInterval>;

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

    // Case 2: plan job was running when user left → resume polling it
    const savedPlanJobId = localStorage.getItem(STORAGE_PLAN_JOB_ID);
    if (savedPlanJobId) {
      const savedFilename = localStorage.getItem(STORAGE_FILENAME) ?? '';
      this.uploadResult.set({ uploadId: '', filename: savedFilename, notes: '', targetSlug: '' });
      this.phase.set('planning');
      this._startPlanPolling(savedPlanJobId);
    }
  }

  ngOnDestroy() {
    this.planStartSub?.unsubscribe();
    if (this.planPollHandle) {
      clearInterval(this.planPollHandle);
      this.planPollHandle = undefined;
    }
    // Keep localStorage — the background job is still running and we need to resume
  }

  onUploaded(result: UploadResult) {
    this.uploadResult.set(result);
    this.phase.set('planning');
    this.planningError.set('');
    localStorage.setItem(STORAGE_FILENAME, result.filename);
    this._startPlanJob(result.uploadId, result.notes, result.targetSlug);
  }

  private _startPlanJob(uploadId: string, notes: string, targetSlug: string) {
    this.planStartSub?.unsubscribe();
    this.planningError.set('');

    this.planStartSub = this.api.startPlanJob(uploadId, notes, targetSlug).subscribe({
      next: (resp) => {
        localStorage.setItem(STORAGE_PLAN_JOB_ID, resp.plan_job_id);
        this._startPlanPolling(resp.plan_job_id);
      },
      error: (err: { status?: number; error?: { detail?: string } }) => {
        if (err.status === 409) {
          // Extremely rare now — another ingestion is already running (not our plan)
          this.planningError.set('Another ingestion is in progress. Please wait and try again.');
        } else {
          this.planningError.set(err?.error?.detail ?? 'Failed to start planning. Try again.');
        }
        this.phase.set('upload');
      },
    });
  }

  private _startPlanPolling(planJobId: string) {
    if (this.planPollHandle) {
      clearInterval(this.planPollHandle);
      this.planPollHandle = undefined;
    }

    this.planPollHandle = setInterval(() => {
      this.api.getPlanJob(planJobId).subscribe({
        next: (job) => {
          if (job.status === 'done') {
            clearInterval(this.planPollHandle);
            this.planPollHandle = undefined;
            localStorage.removeItem(STORAGE_PLAN_JOB_ID);
            this.planResponse.set({ session_id: job.session_id, plan: job.plan });
            this.phase.set('plan-review');
          } else if (job.status === 'error') {
            clearInterval(this.planPollHandle);
            this.planPollHandle = undefined;
            localStorage.removeItem(STORAGE_PLAN_JOB_ID);
            this.planningError.set(job.error_msg || 'Planning failed. Try again.');
            this.phase.set('upload');
          }
          // status === 'running' → keep polling
        },
        error: (err: { status?: number }) => {
          if (err.status === 404) {
            clearInterval(this.planPollHandle);
            this.planPollHandle = undefined;
            localStorage.removeItem(STORAGE_PLAN_JOB_ID);
            this.planningError.set('Plan job expired on server. Please re-upload and try again.');
            this.phase.set('upload');
          }
          // Other HTTP errors: retry on next poll tick
        },
      });
    }, 2000);
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
    if (this.planPollHandle) {
      clearInterval(this.planPollHandle);
      this.planPollHandle = undefined;
    }
    this.planStartSub?.unsubscribe();
    localStorage.removeItem(STORAGE_JOB_ID);
    localStorage.removeItem(STORAGE_FILENAME);
    localStorage.removeItem(STORAGE_PLAN_JOB_ID);
    this.phase.set('upload');
    this.uploadResult.set(null);
    this.planResponse.set(null);
    this.planningError.set('');
  }
}
