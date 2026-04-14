import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.scss'
})
export class NavbarComponent {
  @Input() pageTitle: string = '';
  @Input() loading: boolean = false;
  @Input() todaySessions: number = 0;
  @Input() showMobileMenu: boolean = false;

  @Output() refreshClick = new EventEmitter<void>();
  @Output() mobileMenuToggle = new EventEmitter<void>();

  onRefreshClick(): void {
    this.refreshClick.emit();
  }

  onMobileMenuToggle(): void {
    this.mobileMenuToggle.emit();
  }
}
