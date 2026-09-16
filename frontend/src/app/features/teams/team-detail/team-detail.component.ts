import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TeamsService } from '../../../core/services/teams.service';
import { TeamDetail } from '../../../shared/models/team.model';
import { formatGameVersus } from '../../../shared/utils/game-format';
import { FormatDatePipe } from '../../../shared/pipes/format-date.pipe';
import { LoadingComponent } from '../../../shared/components/loading/loading.component';
import { BreadcrumbComponent, BreadcrumbItem } from '../../../shared/components/breadcrumb/breadcrumb.component';

@Component({
  selector: 'app-team-detail',
  standalone: true,
  imports: [RouterLink, FormatDatePipe, LoadingComponent, BreadcrumbComponent],
  templateUrl: './team-detail.component.html',
  styleUrl: './team-detail.component.scss',
})
export class TeamDetailComponent implements OnInit {
  team: TeamDetail | null = null;
  loading = true;
  error: string | null = null;
  breadcrumbs: BreadcrumbItem[] = [
    { label: 'Accueil', link: '/' },
    { label: 'Équipes', link: '/teams' },
  ];

  constructor(
    private route: ActivatedRoute,
    private teamsService: TeamsService,
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) return;
    this.teamsService.getById(id).subscribe({
      next: (t) => {
        this.team = t;
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.message ?? 'Équipe introuvable';
        this.loading = false;
      },
    });
  }

  playerName(p: { firstName: string; lastName: string; nickname?: string | null }): string {
    return p.nickname?.trim() ? p.nickname : `${p.firstName} ${p.lastName}`;
  }

  formatVersus(g: NonNullable<TeamDetail['recentGames']>[number]): string {
    return formatGameVersus(g);
  }

  scoreDisplay(scores: Array<{ rawScore: string }>): string {
    if (!scores?.length) return '–';
    return scores.map((s) => s.rawScore).join(', ');
  }
}
