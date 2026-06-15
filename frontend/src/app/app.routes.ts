import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
  },
  {
    path: 'partido/:id',
    loadComponent: () =>
      import('./features/partido/partido.component').then(m => m.PartidoComponent),
  },
  {
    path: 'apuestas',
    loadComponent: () =>
      import('./features/apuestas/apuestas.component').then(m => m.ApuestasComponent),
  },
  {
    path: 'torneo',
    loadComponent: () =>
      import('./features/torneo/torneo.component').then(m => m.TorneoComponent),
  },
  {
    path: 'modelo',
    loadComponent: () =>
      import('./features/modelo/modelo.component').then(m => m.ModeloComponent),
  },
  { path: '**', redirectTo: '' },
];
