// super-admin-sidebar.component.ts
import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatButtonModule } from '@angular/material/button';
import { MatToolbarModule } from '@angular/material/toolbar';

@Component({
  selector: 'app-super-admin-sidebar',
  standalone: true,
  imports: [
    CommonModule,
    MatListModule,
    MatIconModule,
    MatDividerModule,
    MatButtonModule,
    MatToolbarModule
  ],
  templateUrl: './super-admin-sidebar.component.html',
  styleUrls: ['./super-admin-sidebar.component.scss']
})
export class SuperAdminSidebarComponent {
  @Input() activeTab: string = 'dashboard';
  @Input() isMobileView: boolean = false;
  @Input() sidebarOpen: boolean = false;
  @Output() tabChanged = new EventEmitter<string>();
  @Output() logoutRequested = new EventEmitter<void>();

  menuItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: 'dashboard',
      description: 'System overview'
    },
    {
      id: 'universities',
      label: 'Universities',
      icon: 'school',
      description: 'Manage universities'
    },
    {
      id: 'users',
      label: 'Users',
      icon: 'people',
      description: 'Manage users & admins'
    },
    {
      id: 'analytics',
      label: 'Analytics',
      icon: 'analytics',
      description: 'Reports & insights'
    }
  ];

  onMenuClick(tabId: string) {
    if (tabId !== this.activeTab) {
      this.tabChanged.emit(tabId);
    }
  }

  constructor(private router: Router) {}

onLogout() {
  console.log('🔧 SuperAdmin logout requested');
  this.logoutRequested.emit();
}
}