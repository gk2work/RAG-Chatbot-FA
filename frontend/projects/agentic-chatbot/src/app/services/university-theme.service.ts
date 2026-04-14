// Create new file: src/app/services/university-theme.service.ts

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, of } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface UniversityBranding {
  university: {
    name: string;
    code: string;
    x_id: string;
  };
  branding: {
    logo_url: string;
    favicon_url: string;
    primary_color: string;
    secondary_color: string;
    accent_color: string;
    font_family: string;
    theme_name: string;
    custom_css: string;
  };
  domains: {
    primary_domain: string;
    subdomain: string;
    custom_domains: string[];
  };
  contact_info: {
    website_url: string;
    support_email: string;
    phone: string;
    address: string;
  };
}

@Injectable({
  providedIn: 'root'
})
export class UniversityThemeService {
  // ✅ FIXED: environment.apiUrl already includes /api, so don't add it again
  private apiUrl = `${environment.apiUrl}/university`;
  private currentBranding$ = new BehaviorSubject<UniversityBranding | null>(null);
  
  // ✅ WHITE-LABEL: Generic default branding (no specific university)
  private defaultBranding: UniversityBranding = {
    university: {
      name: '',  // ✅ Empty for white-label
      code: '',  // ✅ Empty for white-label
      x_id: ''   // ✅ Empty for white-label
    },
    branding: {
      logo_url: '',  // ✅ Empty - no fallback logo
      favicon_url: '',
      primary_color: '#1976d2',  // ✅ Keep basic colors for styling
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

  constructor(private http: HttpClient) {}

  /**
   * Load university branding by X-ID using public endpoint
   */
  loadUniversityBranding(xId: string): Observable<UniversityBranding> {
    console.log('🎨 Loading branding for university:', xId);

    // ✅ FIXED: Use public university endpoint (no auth required)
    const url = `${this.apiUrl}/${xId}/branding`;
    console.log('🔗 Public Branding API URL:', url);
    
    // ✅ FIXED: No authentication required for public endpoint
    // ✅ TEMPORARY: Removed cache-busting headers to fix CORS issue
    const headers = {
      'Content-Type': 'application/json'
    };
    
    return this.http.get<any>(url, { headers }).pipe(
      tap(response => {
        if (response.success) {
          console.log('✅ Branding loaded successfully:', response);
          // Create the proper branding structure
          const brandingData: UniversityBranding = {
            university: response.university,
            branding: response.branding,
            domains: {
              primary_domain: response.branding.primary_domain || '',
              subdomain: response.branding.subdomain || '',
              custom_domains: response.branding.custom_domains || []
            },
            contact_info: {
              website_url: response.branding.website_url || '',
              support_email: response.branding.support_email || '',
              phone: response.branding.phone || '',
              address: response.branding.address || ''
            }
          };
          this.currentBranding$.next(brandingData);
          this.applyTheme(brandingData);
        }
      }),
      catchError(error => {
        console.warn('⚠️ Failed to load branding for X-ID:', xId, error);
        console.warn('⚠️ Using generic white-label branding');
        // ✅ WHITE-LABEL: Use generic branding with the X-ID but no specific university data
        const fallbackBranding = {
          ...this.defaultBranding,
          university: { 
            name: '', // ✅ Empty for white-label
            code: '', // ✅ Empty for white-label  
            x_id: xId // ✅ Keep the requested X-ID
          }
        };
        this.currentBranding$.next(fallbackBranding);
        this.applyTheme(fallbackBranding);
        return of(fallbackBranding);
      })
    );
  }

  /**
   * ✅ NEW: Force refresh university branding (bypasses any caching)
   */
  refreshUniversityBranding(xId: string): Observable<UniversityBranding> {
    console.log('🔄 Force refreshing branding for university:', xId);
    
    // Use timestamp to ensure fresh request
    const url = `${this.apiUrl}/${xId}/branding?t=${Date.now()}`;
    console.log('🔗 Refresh Branding API URL:', url);
    
    const headers = {
      'Content-Type': 'application/json'
    };
    
    return this.http.get<any>(url, { headers }).pipe(
      tap(response => {
        if (response.success) {
          console.log('✅ Branding refreshed successfully:', response);
          const brandingData: UniversityBranding = {
            university: response.university,
            branding: response.branding,
            domains: {
              primary_domain: response.branding.primary_domain || '',
              subdomain: response.branding.subdomain || '',
              custom_domains: response.branding.custom_domains || []
            },
            contact_info: {
              website_url: response.branding.website_url || '',
              support_email: response.branding.support_email || '',
              phone: response.branding.phone || '',
              address: response.branding.address || ''
            }
          };
          this.currentBranding$.next(brandingData);
          this.applyTheme(brandingData);
        }
      }),
      catchError(error => {
        console.warn('⚠️ Failed to refresh branding for X-ID:', xId, error);
        console.warn('⚠️ Falling back to regular load with generic branding');
        // ✅ WHITE-LABEL: Use generic fallback instead of C3S-specific
        const fallbackBranding = {
          ...this.defaultBranding,
          university: { 
            name: '', // ✅ Empty for white-label
            code: '', // ✅ Empty for white-label  
            x_id: xId // ✅ Keep the requested X-ID
          }
        };
        this.currentBranding$.next(fallbackBranding);
        this.applyTheme(fallbackBranding);
        return of(fallbackBranding);
      })
    );
  }

  /**
   * Apply theme to the page using CSS variables
   */
  private applyTheme(branding: UniversityBranding): void {
    const root = document.documentElement;
    const colors = branding.branding;
    
    console.log('🎨 Applying theme with colors:', colors);
    
    // Apply color CSS variables
    root.style.setProperty('--university-primary', colors.primary_color);
    root.style.setProperty('--university-secondary', colors.secondary_color);
    root.style.setProperty('--university-accent', colors.accent_color);
    root.style.setProperty('--university-font', colors.font_family);
    
    // Apply custom CSS if provided
    if (colors.custom_css && colors.custom_css.trim()) {
      this.injectCustomCSS(colors.custom_css);
    }
    
    // Update favicon if provided
    if (colors.favicon_url && colors.favicon_url.trim()) {
      this.updateFavicon(colors.favicon_url);
    }
    
    console.log('🎨 Theme applied for:', branding.university.name);
  }

  /**
   * Inject custom CSS into the page
   */
  private injectCustomCSS(customCSS: string): void {
    // Remove existing custom CSS
    const existingStyle = document.getElementById('university-custom-css');
    if (existingStyle) {
      existingStyle.remove();
    }
    
    // Add new custom CSS
    const style = document.createElement('style');
    style.id = 'university-custom-css';
    style.textContent = customCSS;
    document.head.appendChild(style);
  }

  /**
   * Update page favicon
   */
  private updateFavicon(faviconUrl: string): void {
    const favicon = document.querySelector('link[rel="icon"]') as HTMLLinkElement;
    if (favicon) {
      favicon.href = faviconUrl;
    } else {
      const newFavicon = document.createElement('link');
      newFavicon.rel = 'icon';
      newFavicon.href = faviconUrl;
      document.head.appendChild(newFavicon);
    }
  }

  /**
   * Get current branding as observable
   */
  getCurrentBranding(): Observable<UniversityBranding | null> {
    return this.currentBranding$.asObservable();
  }

  /**
   * Get current branding value (sync)
   */
  getCurrentBrandingValue(): UniversityBranding | null {
    return this.currentBranding$.value;
  }

  /**
   * Reset to default theme
   */
  resetToDefault(): void {
    this.applyTheme(this.defaultBranding);
    this.currentBranding$.next(this.defaultBranding);
  }
}