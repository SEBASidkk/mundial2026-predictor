import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { Standing } from '../../core/models/match.model';

@Component({
  selector: 'app-torneo',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './torneo.component.html',
})
export class TorneoComponent implements OnInit {
  standings: Standing[] = [];
  loading = true;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getStandings().subscribe({
      next: (r) => { this.standings = r.standings; this.loading = false; },
      error: () => { this.loading = false; },
    });
  }

  get sortedStandings(): Standing[] {
    return [...this.standings].sort((a, b) => {
      if (b.Pts !== a.Pts) return b.Pts - a.Pts;
      const gdA = a.GF - a.GA;
      const gdB = b.GF - b.GA;
      if (gdB !== gdA) return gdB - gdA;
      return b.GF - a.GF;
    });
  }
}
