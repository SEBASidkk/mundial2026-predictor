import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <aside class="w-52 flex-shrink-0 border-r p-3 flex flex-col gap-1"
           style="background:#0D1829; border-color:#1E3A5F; min-height:calc(100dvh - 56px);">
      <p class="sbl">Navegación</p>
      <a routerLink="/" routerLinkActive="sa" [routerLinkActiveOptions]="{exact:true}" class="si">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0
               01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
        </svg>
        Dashboard
      </a>
      <a routerLink="/torneo" routerLinkActive="sa" class="si">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0
               002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0
               002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
        </svg>
        Torneo
      </a>
      <p class="sbl mt-3">Sistema</p>
      <a routerLink="/modelo" routerLinkActive="sa" class="si">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3
               m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374
               3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
        </svg>
        Modelo
      </a>
    </aside>
  `,
  styles: [`
    .sbl { font-size:10px; font-weight:600; letter-spacing:0.1em; color:#94A3B8; padding:6px 8px; text-transform:uppercase; }
    .si { display:flex; align-items:center; gap:10px; padding:8px 12px; border-radius:8px; font-size:13px; font-weight:500; color:#94A3B8; text-decoration:none; transition:all 150ms; }
    .si:hover { color:#F8FAFC; background:rgba(255,255,255,0.05); }
    :host ::ng-deep .sa { color:#3B82F6 !important; background:rgba(59,130,246,0.12) !important; }
  `],
})
export class SidebarComponent {}
