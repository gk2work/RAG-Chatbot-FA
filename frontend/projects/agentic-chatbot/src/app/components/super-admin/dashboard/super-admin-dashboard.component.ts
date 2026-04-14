// super-admin-dashboard.component.ts
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatGridListModule } from '@angular/material/grid-list';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { SuperAdminService, DashboardStats } from '../../../services/super-admin.service';

@Component({
  selector: 'app-super-admin-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatGridListModule,
    MatSnackBarModule
  ],
  templateUrl: './super-admin-dashboard.component.html',
  styleUrls: ['./super-admin-dashboard.component.scss']
})
export class SuperAdminDashboardComponent implements OnInit {
  loading = true;
  error = '';
  stats: DashboardStats['stats'] | null = null;
  lastUpdated: Date | null = null;

  constructor(
    private superAdminService: SuperAdminService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.loadDashboardData();
  }

  loadDashboardData() {
    this.loading = true;
    this.error = '';

    this.superAdminService.getDashboardStats().subscribe({
      next: (response: DashboardStats) => {
        if (response.success && response.stats) {
          this.stats = response.stats;
          this.lastUpdated = new Date();
          this.loading = false;
          console.log('✅ Dashboard data loaded successfully:', response.stats);
        } else {
          this.error = 'Invalid response format from server';
          this.loading = false;
        }
      },
      error: (error: Error) => {
        this.error = error.message;
        this.loading = false;
        console.error('❌ Failed to load dashboard data:', error);
        
        // Show error notification
        this.snackBar.open(
          `Failed to load dashboard: ${error.message}`, 
          'Close', 
          { duration: 5000 }
        );
      }
    });
  }

  refreshData() {
    console.log('🔄 Refreshing dashboard data...');
    this.loadDashboardData();
  }
}