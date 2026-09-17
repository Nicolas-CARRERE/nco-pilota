import { Component, OnInit } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartData } from 'chart.js';
import { StatsService, DisciplineStats } from '../../core/services/stats.service';
import { DashboardFilterStateService, DashboardFilters } from '../../core/services/dashboard-filter-state.service';

@Component({
  selector: 'app-disciplines',
  standalone: true,
  imports: [BaseChartDirective],
  templateUrl: './disciplines.component.html',
  styleUrl: './disciplines.component.scss',
})
export class DisciplinesComponent implements OnInit {
  disciplines: DisciplineStats[] = [];
  loading = false;

  public pieChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom' },
      tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${ctx.parsed} games` } },
    },
  };

  public pieChartData: ChartData<'pie'> = { labels: [], datasets: [{ data: [], label: 'Games' }] };

  constructor(private statsService: StatsService, private filterService: DashboardFilterStateService) {}

  ngOnInit(): void {
    this.filterService.getFilters().subscribe((filters: DashboardFilters) => this.loadDisciplines(filters));
  }

  loadDisciplines(filters: DashboardFilters): void {
    this.loading = true;
    this.statsService.getDisciplineStats(filters).subscribe({
      next: (response) => {
        this.disciplines = response.disciplines;
        this.pieChartData.labels = response.disciplines.map((d) => d.discipline_name);
        this.pieChartData.datasets[0].data = response.disciplines.map((d) => d.games_count);
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }
}
