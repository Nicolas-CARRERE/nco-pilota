import { Component, OnInit } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartData } from 'chart.js';
import { StatsService, PlayerStats } from '../../core/services/stats.service';
import { DashboardFilterStateService, DashboardFilters } from '../../core/services/dashboard-filter-state.service';

@Component({
  selector: 'app-top-players',
  standalone: true,
  imports: [BaseChartDirective],
  templateUrl: './top-players.component.html',
  styleUrl: './top-players.component.scss',
})
export class TopPlayersComponent implements OnInit {
  players: PlayerStats[] = [];
  loading = false;

  public barChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `${ctx.parsed.y} wins` } },
    },
  };

  public barChartData: ChartData<'bar'> = { labels: [], datasets: [{ data: [], label: 'Wins' }] };

  constructor(private statsService: StatsService, private filterService: DashboardFilterStateService) {}

  ngOnInit(): void {
    this.filterService.getFilters().subscribe((filters: DashboardFilters) => this.loadPlayers(filters));
  }

  loadPlayers(filters: DashboardFilters): void {
    this.loading = true;
    this.statsService.getTopPlayers(10, filters).subscribe({
      next: (response) => {
        this.players = response.players;
        this.barChartData.labels = response.players.map((p) => `${p.firstName} ${p.lastName}`);
        this.barChartData.datasets[0].data = response.players.map((p) => p.wins);
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }
}
