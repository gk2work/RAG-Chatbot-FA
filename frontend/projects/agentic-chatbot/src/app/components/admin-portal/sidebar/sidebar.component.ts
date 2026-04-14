import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
// ✅ ADD: Import UniversityThemeService for live branding
import { UniversityThemeService, UniversityBranding } from '../../../services/university-theme.service';
// ✅ ADD: Import environment for API URL
import { environment } from '../../../../environments/environment';

// ✅ REMOVE: Old interface, use the proper one from service
// interface UniversityBranding {
//   name: string;
//   code: string;
//   logo_url?: string;
//   branding?: {
//     logo_url?: string;
//     primary_color?: string;
//     secondary_color?: string;
//   };
// }

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss'
})
export class SidebarComponent implements OnInit {
  @Input() sidebarCollapsed: boolean = false;
  @Input() activeTab: string = 'dashboard';
  @Input() totalLeads: number = 0;
  @Input() totalSessions: number = 0;
  @Input() universitiesCount: number = 0;
  @Output() tabChange = new EventEmitter<string>();
  @Output() sidebarToggle = new EventEmitter<void>();

  // ✅ University branding properties - use proper interface
  universityBranding: UniversityBranding | null = null;
  brandingLoaded = false;

  // ✅ ADD: Inject UniversityThemeService
  constructor(
    private router: Router,
    private themeService: UniversityThemeService
  ) {}

  ngOnInit() {
    this.loadUniversityBranding();
  }

  // ✅ FIXED: Load live branding data from API
  private loadUniversityBranding() {
    // Get university context from localStorage
    const adminUniversityContext = JSON.parse(localStorage.getItem('adminUniversityContext') || 'null');
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');
    
    if (adminUniversityContext && currentUser && adminUniversityContext.x_id) {
      console.log('🏛️ Loading live branding for admin portal:', adminUniversityContext.x_id);
      
      // ✅ FIXED: Use UniversityThemeService to get live branding data
      this.themeService.loadUniversityBranding(adminUniversityContext.x_id).subscribe({
        next: (branding) => {
          this.universityBranding = branding;
          this.brandingLoaded = true;
          console.log('✅ Admin portal branding loaded:', branding);
        },
        error: (error) => {
          console.error('❌ Failed to load admin portal branding:', error);
          console.log('🔄 Using fallback branding for admin portal');
          
          // ✅ IMPROVED: Better fallback with university context
          this.universityBranding = {
            university: {
              name: adminUniversityContext.name || '', // ✅ WHITE-LABEL: Empty if no name
              code: adminUniversityContext.code || '',
              x_id: adminUniversityContext.x_id
            },
            branding: {
              logo_url: '', // ✅ WHITE-LABEL: Empty logo
              favicon_url: '',
              primary_color: '#1976d2',
              secondary_color: '#424242',
              accent_color: '#ff4081',
              font_family: 'Roboto, sans-serif',
              theme_name: 'default',
              custom_css: ''
            },
            domains: {
              primary_domain: '',
              subdomain: '',
              custom_domains: []
            },
            contact_info: {
              website_url: '',
              support_email: '',
              phone: '',
              address: ''
            }
          };
          this.brandingLoaded = true;
        }
      });
    } else {
      console.warn('⚠️ No admin university context found');
      this.brandingLoaded = true;
    }
  }

  // ✅ FIXED: Get university logo with proper fallback chain
  getUniversityLogo(): string {
    // ✅ Use proper branding structure
    const logoUrl = this.universityBranding?.branding?.logo_url;
    
    if (logoUrl && logoUrl.trim()) {
      // ✅ Handle both relative and absolute URLs
      if (logoUrl.startsWith('/uploads/')) {
        // ✅ FIXED: Remove /api from environment.apiUrl since uploads are served at root level
        const baseUrl = environment.apiUrl.replace('/api', ''); // Remove /api suffix to get base URL
        return `${baseUrl}${logoUrl}`;
      }
      return logoUrl;
    }
    
    // ✅ WHITE-LABEL: Return empty string instead of fallback logo
    return '';
  }

  // ✅ FIXED: Get university name with proper fallback
  getUniversityName(): string {
    const name = this.universityBranding?.university?.name;
    // ✅ WHITE-LABEL: Show generic text if no university name
    return name && name.trim() ? name : 'Admin Portal';
  }

  // ✅ Get university alt text - Fixed return type
  getLogoAltText(): string {
    const name = this.universityBranding?.university?.name;
    // ✅ WHITE-LABEL: Generic alt text if no university name
    return name && name.trim() ? `${name} Logo` : 'University Logo';
  }

  // ✅ Fixed image error handler with proper typing
  onImageError(event: Event) {
    console.warn('⚠️ Admin portal logo failed to load');
    const target = event.target as HTMLImageElement;
    if (target) {
      // ✅ WHITE-LABEL: Hide image instead of showing fallback logo
      target.style.display = 'none';
    }
  }

  setActiveTab(tab: string): void {
    this.tabChange.emit(tab);
  }

  toggleSidebar(): void {
    this.sidebarToggle.emit();
  }

  onLogout() {
    console.log('Admin logout requested');
    
    // Clear all stored data
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    localStorage.removeItem('adminUniversityContext');
    
    // Navigate to login page
    this.router.navigate(['/auth/login']);
  }
}