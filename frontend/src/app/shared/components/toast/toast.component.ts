import { Component, inject } from '@angular/core';
import { ToastService, Toast } from '../../../core/services/toast.service';
import { NgClass, NgIf } from '@angular/common';

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [NgClass, NgIf],
  templateUrl: './toast.component.html',
  styleUrl: './toast.component.scss',
})
export class ToastComponent {
  private toastService = inject(ToastService);

  readonly toasts = this.toastService.toasts;

  getIcon(type: string): string {
    switch (type) {
      case 'success':
        return '✓';
      case 'error':
        return '✕';
      case 'warning':
        return '⚠';
      default:
        return 'ℹ';
    }
  }

  remove(id: number): void {
    this.toastService.remove(id);
  }
}
