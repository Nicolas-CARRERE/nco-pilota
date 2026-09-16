import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TeamsService } from '../../../core/services/teams.service';
import { TeamListItem } from '../../../shared/models/team.model';
import { LoadingComponent } from '../../../shared/components/loading/loading.component';
import { FilterComponent, FilterConfig } from '../../../shared/components/filter/filter.component';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-team-list',
  standalone: true,
  imports: [RouterLink, LoadingComponent, FilterComponent],
  templateUrl: './team-list.component.html',
  styleUrl: './team-list.component.scss',
})
export class TeamListComponent implements OnInit {
  teams: TeamListItem[] = [];
  total = 0;
  loading = true;
  error: string | null = null;
  filters: Record<string, any> = {};
  filterConfig: FilterConfig = { showCompetition: true, compact: true };
  searchQuery = '';

  constructor(
    private teamsService: TeamsService,
    private toastService: ToastService,
  ) {}

  ngOnInit(): void {
    this.loadTeams();
  }

  applyFilters(newFilters: Record<string, any>): void {
    this.filters = { ...this.filters, ...newFilters };
    this.loadTeams();
  }

  onResetFilters(): void {
    this.filters = {};
    this.searchQuery = '';
    this.toastService.info('Filtres réinitialisés');
    this.loadTeams();
  }

  onSearchChange(query: string): void {
    this.searchQuery = query;
    this.loadTeams();
  }

  loadTeams(): void {
    this.loading = true;
    const params: any = { limit: 200 };
    if (this.searchQuery.trim()) {
      params.search = this.searchQuery.trim();
    }
    this.teamsService.getList(params).subscribe({
      next: (res) => {
        this.teams = res.teams ?? [];
        this.total = res.total ?? 0;
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.message ?? 'Erreur lors du chargement';
        this.loading = false;
      },
    });
  }
}
