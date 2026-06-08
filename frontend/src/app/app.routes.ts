import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'ask', pathMatch: 'full' },
  {
    path: 'login',
    loadComponent: () => import('./features/login/login').then(m => m.Login),
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
    canActivate: [authGuard],
    loadComponent: () => import('./features/admin/admin-dashboard').then(m => m.AdminDashboard),
  },
  {
    path: 'dashboard',
    canActivate: [authGuard],
    loadComponent: () => import('./features/traces/dashboard').then(m => m.Dashboard),
  },
  {
    path: 'traces',
    canActivate: [authGuard],
    loadComponent: () => import('./features/traces/trace-list').then(m => m.TraceList),
  },
  {
    path: 'traces/:traceId',
    canActivate: [authGuard],
    loadComponent: () => import('./features/traces/trace-detail').then(m => m.TraceDetail),
  },
  {
    path: 'ingest',
    canActivate: [authGuard],
    loadComponent: () => import('./features/ingest/ingest').then(m => m.Ingest),
  },
  {
    path: 'graph',
    canActivate: [authGuard],
    loadComponent: () => import('./features/graph/graph-page').then(m => m.GraphPage),
  },
  { path: '**', redirectTo: 'ask' },
];
