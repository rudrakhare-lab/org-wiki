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
  { path: '**', redirectTo: 'ask' },
];
