import {
  AfterViewInit,
  Component,
  ElementRef,
  HostListener,
  OnDestroy,
  ViewChild,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService, WikiGraphData, WikiGraphNode } from '../../core/api.service';
import { Subscription } from 'rxjs';

const TYPE_COLORS: Record<string, string> = {
  module:          '#4A90E2',
  entity:          '#7ED321',
  concept:         '#9B59B6',
  config:          '#F39C12',
  decision:        '#E74C3C',
  source:          '#7F8C8D',
  'cross-module':  '#1ABC9C',
  integration:     '#F1C40F',
  person:          '#E91E63',
  pattern:         '#FF7043',
};

const DEFAULT_COLOR = '#BDC3C7';

@Component({
  selector: 'app-graph-page',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './graph-page.html',
  styleUrl: './graph-page.scss',
})
export class GraphPage implements AfterViewInit, OnDestroy {
  private api = inject(ApiService);

  @ViewChild('graphContainer') graphContainer!: ElementRef<HTMLDivElement>;

  loading = signal(true);
  nodeCount = signal(0);
  edgeCount = signal(0);
  errorMsg = signal('');

  modalOpen = signal(false);
  selectedNode = signal<WikiGraphNode | null>(null);
  pageLoading = signal(false);
  pageContent = signal('');
  pageError = signal('');

  readonly TYPE_COLORS = TYPE_COLORS;
  readonly DEFAULT_COLOR = DEFAULT_COLOR;

  readonly legendItems = Object.entries(TYPE_COLORS).map(([type, color]) => ({
    type,
    color,
    label: type.charAt(0).toUpperCase() + type.slice(1),
  }));

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private graphInstance: any;
  private resizeObserver?: ResizeObserver;
  private dataSub?: Subscription;
  private pageSub?: Subscription;

  ngAfterViewInit() {
    this.dataSub = this.api.getWikiGraph().subscribe({
      next: (data) => {
        this.nodeCount.set(data.nodes.length);
        this.edgeCount.set(data.links.length);
        this.initGraph(data);
      },
      error: () => {
        this.loading.set(false);
        this.errorMsg.set('Failed to load graph data.');
      },
    });
  }

  ngOnDestroy() {
    this.dataSub?.unsubscribe();
    this.pageSub?.unsubscribe();
    this.resizeObserver?.disconnect();
    // force-graph doesn't expose a destroy method; GC handles the canvas
  }

  private async initGraph(data: WikiGraphData) {
    // force-graph exports a callable factory; cast to avoid TS2348
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const fg = await import('force-graph') as any;
    const ForceGraph = fg.default ?? fg;
    const container = this.graphContainer.nativeElement;

    this.graphInstance = ForceGraph()(container)
      .width(container.clientWidth)
      .height(container.clientHeight)
      .backgroundColor('#0d1117')
      .graphData(data)
      .nodeLabel((node: unknown) => {
        const n = node as WikiGraphNode;
        return `${n.label} (${n.type})`;
      })
      .nodeColor((node: unknown) => {
        const n = node as WikiGraphNode;
        return TYPE_COLORS[n.type] ?? DEFAULT_COLOR;
      })
      .nodeVal((node: unknown) => (node as WikiGraphNode).val)
      .nodeRelSize(4)
      .linkColor(() => 'rgba(100,120,150,0.25)')
      .linkWidth(1)
      .onNodeHover((node: unknown) => {
        container.style.cursor = node ? 'pointer' : 'default';
      })
      .onNodeClick((node: unknown) => this.openModal(node as WikiGraphNode));

    this.resizeObserver = new ResizeObserver(() => {
      if (this.graphInstance) {
        this.graphInstance
          .width(container.clientWidth)
          .height(container.clientHeight);
      }
    });
    this.resizeObserver.observe(container);

    this.loading.set(false);
  }

  openModal(node: WikiGraphNode) {
    this.selectedNode.set(node);
    this.modalOpen.set(true);
    this.pageContent.set('');
    this.pageError.set('');
    this.pageLoading.set(true);

    this.pageSub?.unsubscribe();
    this.pageSub = this.api.getWikiPage(node.path).subscribe({
      next: (page) => {
        this.pageContent.set(page.content);
        this.pageLoading.set(false);
      },
      error: () => {
        this.pageError.set('Could not load page content.');
        this.pageLoading.set(false);
      },
    });
  }

  closeModal() {
    this.modalOpen.set(false);
    this.selectedNode.set(null);
    this.pageContent.set('');
    this.pageSub?.unsubscribe();
  }

  nodeColor(node: WikiGraphNode | null): string {
    if (!node) return DEFAULT_COLOR;
    return TYPE_COLORS[node.type] ?? DEFAULT_COLOR;
  }

  @HostListener('document:keydown.escape')
  onEscape() {
    if (this.modalOpen()) this.closeModal();
  }
}
