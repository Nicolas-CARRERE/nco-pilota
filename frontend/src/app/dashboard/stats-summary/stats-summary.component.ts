import { Component, OnInit } from '@angular/core';
import { StatsService, SummaryStats } from '../../core/services/stats.service';
import { DashboardFilterStateService, DashboardFilters } from '../../core/services/dashboard-filter-state.service';

@Component({
  selector: 'app-stats-summary',
  standalone: true,
  imports: [],
  templateUrl: './stats-summary.component.html',
  styleUrl: './stats-summary.component.scss',
})
export class StatsSummaryComponent implements OnInit {
  stats: SummaryStats = { total_games: 0, total_players: 0, total_clubs: 0, total_competitions: 0, total_disciplines: 0 };
  loading = false;

  constructor(private statsService: StatsService, private filterService: DashboardFilterStateService) {}

  ngOnInit(): void {
    this.filterService.getFilters().subscribe((filters: DashboardFilters) => this.loadStats(filters));
  }

  loadStats(filters: DashboardFilters): void {
    this.loading = true;
    this.statsService.getSummary(filters).subscribe({
      next: (data: SummaryStats) => {
        this.stats = data;
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }
}
