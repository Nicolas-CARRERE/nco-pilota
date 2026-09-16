import { Component, Input } from '@angular/core';
import { NgClass, NgIf, NgFor } from '@angular/common';

@Component({
  selector: 'app-skeleton',
  standalone: true,
  imports: [NgClass, NgIf, NgFor],
  templateUrl: './skeleton.component.html',
  styleUrl: './skeleton.component.scss',
})
export class SkeletonComponent {
  @Input() variant: 'card' | 'list' | 'text' | 'avatar' = 'card';
  @Input() count: number = 1;
  @Input() height: string = '100px';
  @Input() lines: number = 3;
}
