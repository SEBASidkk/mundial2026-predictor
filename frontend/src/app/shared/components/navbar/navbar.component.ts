import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <nav class="flex items-center justify-between px-6 h-14 border-b"
         style="background:#0D1829; border-color:#1E3A5F; position:sticky; top:0; z-index:100;">
      <span class="font-mono font-bold text-base tracking-wide" style="color:#3B82F6">
        MUNDIAL<span style="color:#D97706">2026</span>
      </span>
      <div class="flex gap-1">
        <a routerLink="/" routerLinkActive="nav-active" [routerLinkActiveOptions]="{exact:true}"
           class="nav-link">Dashboard</a>
        <a routerLink="/torneo" routerLinkActive="nav-active" class="nav-link">Torneo</a>
        <a routerLink="/modelo" routerLinkActive="nav-active" class="nav-link">Modelo</a>
      </div>
      <div class="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono"
           style="background:rgba(34,197,94,0.1); border:1px solid rgba(34,197,94,0.25); color:#22C55E;">
        <span class="w-1.5 h-1.5 rounded-full animate-pulse" style="background:#22C55E;"></span>
        72 predicciones activas
      </div>
    </nav>
  `,
  styles: [`
    .nav-link {
      padding: 6px 14px; border-radius: 6px; font-size: 13px;
      font-weight: 500; color: #94A3B8; text-decoration: none; transition: all 150ms;
    }
    .nav-link:hover { color: #F8FAFC; background: rgba(255,255,255,0.05); }
    :host ::ng-deep .nav-active { color: #3B82F6 !important; background: rgba(59,130,246,0.12) !important; }
  `],
})
export class NavbarComponent {}
