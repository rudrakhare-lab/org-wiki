import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, IngestPlanResponse } from '../../core/api.service';
import { inject } from '@angular/core';
import { UploadStep, UploadResult } from './upload-step';
import { PlanStep } from './plan-step';
import { ExecuteStep } from './execute-step';

type IngestPhase = 'upload' | 'planning' | 'plan-review' | 'executing';

@Component({
  selector: 'app-ingest',
  standalone: true,
  imports: [CommonModule, UploadStep, PlanStep, ExecuteStep],
  templateUrl: './ingest.html',
  styleUrl: './ingest.scss',
})
export class Ingest {
  private api = inject(ApiService);

  phase = signal<IngestPhase>('upload');
  uploadResult = signal<UploadResult | null>(null);
  planResponse = signal<IngestPlanResponse | null>(null);
  planningError = signal('');

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
    this.phase.set('upload');
    this.uploadResult.set(null);
    this.planResponse.set(null);
    this.planningError.set('');
  }
}
