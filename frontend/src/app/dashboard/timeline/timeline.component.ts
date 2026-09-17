import { Component, OnInit } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartData } from 'chart.js';
import { StatsService, TimelineStats } from '../../core/services/stats.service';
import { DashboardFilterStateService, DashboardFilters } from '../../core/services/dashboard-filter-state.service';

@Component({
  selector: 'app-timeline',
  standalone: true,
  imports: [BaseChartDirective],
  templateUrl: './timeline.component.html',
  styleUrl: './timeline.component.scss',
})
export class TimelineComponent implements OnInit {
  timeline: TimelineStats[] = [];
  loading = false;

  public lineChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `${ctx.parsed.y} games` } },
    },
  };

  public lineChartData: ChartData<'line'> = { labels: [], datasets: [{ data: [], label: 'Games Over Time' }] };

  constructor(private statsService: StatsService, private filterService: DashboardFilterStateService) {}

  ngOnInit(): void {
    this.filterService.getFilters().subscribe((filters: DashboardFilters) => this.loadTimeline(filters));
  }

  loadTimeline(filters: DashboardFilters): void {
    this.loading = true;
    this.statsService.getTimelineStats(filters).subscribe({
      next: (response) => {
        this.timeline = response.timeline;
        this.lineChartData.labels = response.timeline.map((t) => t.month);
        this.lineChartData.datasets[0].data = response.timeline.map((t) => t.games_count);
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }
}
