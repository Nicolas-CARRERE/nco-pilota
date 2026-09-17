import { Component, OnInit } from '@angular/core';
import { FilterComponent, FilterConfig } from '../../shared/components/filter/filter.component';
import { DashboardFilterStateService, DashboardFilters } from '../../core/services/dashboard-filter-state.service';

@Component({
  selector: 'app-filter-panel',
  standalone: true,
  imports: [FilterComponent],
  templateUrl: './filter-panel.component.html',
  styleUrl: './filter-panel.component.scss',
})
export class FilterPanelComponent implements OnInit {
  filters: DashboardFilters = {};
  filterConfig: FilterConfig = {
    showCompetition: true,
    showDiscipline: true,
    showSeason: true,
    showPhase: true,
    showDateRange: true,
    compact: false,
  };

  constructor(private filterService: DashboardFilterStateService) {}

  ngOnInit(): void {
    this.filterService.getFilters().subscribe((f: DashboardFilters) => {
      this.filters = { ...f };
    });
  }

  onFiltersChange(newFilters: Record<string, any>): void {
    this.filters = { ...this.filters, ...newFilters };
    this.filterService.updateFilters(this.filters);
  }
}
