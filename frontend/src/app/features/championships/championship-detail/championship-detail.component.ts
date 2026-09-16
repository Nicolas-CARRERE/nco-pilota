import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CompetitionsService } from '../../../core/services/competitions.service';
import { CompetitionDetail } from '../../../shared/models/competition.model';
import { formatGameVersus } from '../../../shared/utils/game-format';
import { FormatDatePipe } from '../../../shared/pipes/format-date.pipe';
import { LoadingComponent } from '../../../shared/components/loading/loading.component';
import { BreadcrumbComponent, BreadcrumbItem } from '../../../shared/components/breadcrumb/breadcrumb.component';

@Component({
  selector: 'app-championship-detail',
  standalone: true,
  imports: [RouterLink, FormatDatePipe, LoadingComponent, BreadcrumbComponent],
  templateUrl: './championship-detail.component.html',
  styleUrl: './championship-detail.component.scss',
})
export class ChampionshipDetailComponent implements OnInit {
  competition: CompetitionDetail | null = null;
  loading = true;
  error: string | null = null;
  breadcrumbs: BreadcrumbItem[] = [
    { label: 'Accueil', link: '/' },
    { label: 'Championnats', link: '/championships' },
  ];

  constructor(
    private route: ActivatedRoute,
    private competitionsService: CompetitionsService,
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) return;
    this.competitionsService.getById(id).subscribe({
      next: (c) => {
        this.competition = c;
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.message ?? 'Championnat introuvable';
        this.loading = false;
      },
    });
  }

  formatVersus(g: NonNullable<CompetitionDetail['recentGames']>[number]): string {
    return formatGameVersus(g);
  }

  scoreDisplay(scores: Array<{ rawScore: string }>): string {
    if (!scores?.length) return '–';
    return scores.map((s) => s.rawScore).join(', ');
  }
}
