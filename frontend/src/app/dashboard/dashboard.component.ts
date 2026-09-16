import { Component, OnInit } from '@angular/core';
import { DashboardFilterService, DashboardFilters } from '../core/services/filter.service';
import { StatsSummaryComponent } from './stats-summary/stats-summary.component';
import { FilterPanelComponent } from './filter-panel/filter-panel.component';
import { TopPlayersComponent } from './top-players/top-players.component';
import { TopClubsComponent } from './top-clubs/top-clubs.component';
import { TimelineComponent } from './timeline/timeline.component';
import { DisciplinesComponent } from './disciplines/disciplines.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    StatsSummaryComponent,
    FilterPanelComponent,
    TopPlayersComponent,
    TopClubsComponent,
    TimelineComponent,
    DisciplinesComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  filters: DashboardFilters = {};
  sidebarCollapsed = false;

  constructor(private filterService: DashboardFilterService) {}

  ngOnInit(): void {
    this.filterService.getFilters().subscribe((filters: DashboardFilters) => {
      this.filters = filters;
    });
  }

  toggleSidebar(): void {
    this.sidebarCollapsed = !this.sidebarCollapsed;
  }

  onMainClick(): void {
    // Close sidebar on mobile when clicking main content
    if (window.innerWidth <= 768 && !this.sidebarCollapsed) {
      this.sidebarCollapsed = true;
    }
  }
}
