import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';
import { roleGuard, pendingGuard } from './core/role.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'ask', pathMatch: 'full' },
  {
    path: 'login',
    loadComponent: () => import('./features/login/login').then(m => m.Login),
  },
  {
    path: 'pending',
    canActivate: [pendingGuard],
    loadComponent: () => import('./features/pending/pending').then(m => m.Pending),
  },
  {
    path: 'ask',
    canActivate: [authGuard],
    loadComponent: () => import('./features/ask/ask').then(m => m.Ask),
  },
  {
    path: 'search',
    canActivate: [authGuard],
    loadComponent: () => import('./features/search/search').then(m => m.Search),
  },
  {
    path: 'admin',
    canActivate: [authGuard, roleGuard(['admin'])],
    loadComponent: () => import('./features/admin/admin-dashboard').then(m => m.AdminDashboard),
  },
  {
    path: 'admin/agents',
    canActivate: [authGuard, roleGuard(['admin'])],
    loadComponent: () => import('./features/admin/manage-agents').then(m => m.ManageAgents),
  },
  {
    path: 'dashboard',
    canActivate: [authGuard, roleGuard(['admin'])],
    loadComponent: () => import('./features/traces/dashboard').then(m => m.Dashboard),
  },
  {
    path: 'traces',
    canActivate: [authGuard, roleGuard(['admin'])],
    loadComponent: () => import('./features/traces/trace-list').then(m => m.TraceList),
  },
  {
    path: 'traces/:traceId',
    canActivate: [authGuard, roleGuard(['admin'])],
    loadComponent: () => import('./features/traces/trace-detail').then(m => m.TraceDetail),
  },
  {
    path: 'ingest',
    canActivate: [authGuard, roleGuard(['admin', 'developer'])],
    loadComponent: () => import('./features/ingest/ingest').then(m => m.Ingest),
  },
  {
    path: 'graph',
    canActivate: [authGuard, roleGuard(['admin', 'developer', 'general'])],
    loadComponent: () => import('./features/graph/graph-page').then(m => m.GraphPage),
  },
  { path: '**', redirectTo: 'ask' },
];
