// super-admin.component.ts
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { SuperAdminSidebarComponent } from './sidebar/super-admin-sidebar.component';
import { SuperAdminDashboardComponent } from './dashboard/super-admin-dashboard.component';
import { SuperAdminUniversitiesComponent } from './universities/super-admin-universities.component';
import { SuperAdminUsersComponent } from './users/super-admin-users.component';
import { SuperAdminAnalyticsComponent } from './analytics/super-admin-analytics.component';




@Component({
  selector: 'app-super-admin',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    SuperAdminSidebarComponent,
    SuperAdminDashboardComponent,
    SuperAdminUniversitiesComponent,
    SuperAdminUsersComponent,
    SuperAdminAnalyticsComponent
  ],
  templateUrl: './super-admin.component.html',
  styleUrls: ['./super-admin.component.scss']
})
export class SuperAdminComponent implements OnInit {
  activeTab: string = 'dashboard';
  loading: boolean = false;
  error: string = '';
  sidebarOpen: boolean = false;
  isMobileView: boolean = false;

  constructor(
    private router: Router,
    private route: ActivatedRoute
  ) {
    this.checkMobileView();
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', () => this.checkMobileView());
    }
  }

  ngOnInit() {
    console.log('🔧 SuperAdmin Component Initializing...');
    
    // Get active tab from route data or query params
    this.activeTab = this.route.snapshot.data['activeTab'] || 
                     this.route.snapshot.queryParams['tab'] || 
                     'dashboard';

    console.log('📍 SuperAdmin Active Tab:', this.activeTab);

    // Check if User has auth token
    this.checkAuthentication();
  }

  private checkAuthentication() {
    const token = localStorage.getItem('authToken');
    const currentUser = localStorage.getItem('currentUser');
    
    console.log('🔐 Auth Check:', {
      tokenExists: !!token,
      userExists: !!currentUser,
      token: token ? `${token.substring(0, 20)}...` : 'None'
    });
    
    if(!token) {
        this.error = 'Please login as SuperAdmin to access this page';
        console.log('❌ No auth token found');
    } else {
        console.log('✅ Auth token found, component should load normally');
    }
  }

  onTabChange(tab: string) {
    this.activeTab = tab;
    this.error = ''; // Clear any errors when switching tabs
    
    // Update URL without reloading page
    this.router.navigate(['/superadmin'], { 
      queryParams: { tab: tab },
      replaceUrl: true 
    });
  }

  retry() {
    this.error = '';
    this.loading = true;
    // Retry logic will be implemented when we add services
    setTimeout(() => {
      this.loading = false;
    }, 1000);
  }

  // Mobile responsiveness methods
  private checkMobileView() {
    if (typeof window !== 'undefined') {
      this.isMobileView = window.innerWidth <= 768;
      if (!this.isMobileView) {
        this.sidebarOpen = false;
      }
    }
  }

  toggleSidebar() {
    this.sidebarOpen = !this.sidebarOpen;
  }

  closeSidebar() {
    this.sidebarOpen = false;
  }

  getPageTitle(): string {
    const titles: { [key: string]: string } = {
      'dashboard': 'Dashboard',
      'universities': 'Universities',
      'users': 'Users',
      'analytics': 'Analytics'
    };
    return titles[this.activeTab] || 'SuperAdmin';
  }

  onLogout() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    localStorage.removeItem('adminUniversityContext');
    this.router.navigate(['/auth/login']);
  }
}