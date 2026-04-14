// super-admin.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface DashboardStats {
  success: boolean;
  stats: {
    system_overview: {
      total_universities: number;
      total_users: number;
      total_leads: number;
      total_sessions: number;
      active_sessions: number;
      total_documents: number;
    };
    recent_activity: {
      new_universities_today: number;
      new_leads_today: number;
      active_sessions_today: number;
    };
    user_breakdown: {
      superadmins: number;
      admins: number;
      students: number;
    };
    ai_services: {
      enhanced_rag_available: boolean;
      pdf_service_available: boolean;
      vector_search_enabled: boolean;
      universities_with_ai: number;
      rag_status?: {
        healthy: boolean;
        message: string;
      };
    };
    document_processing?: {
      universities_with_documents: number;
      average_chunks_per_university: number;
      total_processed_chunks: number;
    };
  };
  system_health: {
    database_connected: boolean;
    ai_services_operational: boolean;
    document_processing_available: boolean;
  };
  timestamp: string;
}

// Legacy interface for backward compatibility
export interface AnalyticsData {
  success: boolean;
  data: {
    leads: {
      total: number;
      recent: number;
      by_university: Array<{_id: string, count: number, university_name?: string}>;
      by_country: Array<{_id: string, count: number}>;
    };
    sessions: {
      total: number;
      active: number;
      recent: number;
      by_university: Array<{_id: string, count: number, avg_messages: number, university_name?: string}>;
    };
    users: {
      total: number;
      by_university: Array<{_id: string, total_users: number, admins: number, students: number, university_name?: string}>;
    };
  };
  timestamp: string;
}

export interface EnhancedAnalyticsData {
  success: boolean;
  analytics: {
    date_range: {
      days: number;
      start_date: string;
      end_date: string;
    };
    leads: {
      total_leads: number;
      recent_leads: number;
      leads_by_university: Array<{_id: string, count: number, recent_count: number}>;
      leads_by_country: Array<{_id: string, count: number}>;
      conversion_trends: Array<any>;
    };
    sessions: {
      total_sessions: number;
      active_sessions: number;
      recent_sessions: number;
      sessions_by_university: Array<{_id: string, count: number, avg_messages: number, total_messages: number}>;
      engagement_metrics: Array<any>;
    };
    ai_services: {
      total_universities: number;
      ai_enabled_universities: number;
      total_documents: number;
      universities_with_documents: number;
      document_distribution?: Array<any>;
    };
    performance: {
      system_health: any;
      resource_utilization: any;
    };
    insights: {
      top_performing_universities: Array<any>;
      universities_needing_attention: Array<any>;
      growth_trends: any;
      recommendations: Array<any>;
    };
  };
  generated_at: string;
}

export interface UniversityDetails {
  success: boolean;
  university: {
    _id: string;
    name: string;
    code: string;
    x_id: string;
    description?: string;
    status?: string;
    branding?: any;
    ai_config?: any;
    contact_info?: any;
    detailed_stats: {
      leads: any;
      sessions: any;
      users: any;
    };
    document_analytics?: {
      total_chunks: number;
      documents_by_type: Array<any>;
      recent_uploads: Array<any>;
    };
    ai_analytics?: {
      rag_config: any;
      vectorstore_stats: any;
      features: any;
      health_status: any;
    };
    branding_analysis: {
      completeness_score: number;
      configured_elements: string[];
      missing_elements: string[];
      recommendations: Array<any>;
    };
  };
}

export interface SystemHealthStatus {
  overall_health: 'healthy' | 'warning' | 'degraded' | 'critical';
  services: any;
  databases: any;
  ai_services: any;
  performance_metrics: any;
  issues: string[];
  issue_count: number;
  recommendations: Array<{
    priority: 'high' | 'medium' | 'low';
    category: string;
    message: string;
  }>;
  checked_at: string;
}

export interface UserManagement {
  success: boolean;
  users: Array<any>;
  pagination: {
    current_page: number;
    total_pages: number;
    total_count: number;
    has_next: boolean;
  };
  analytics: {
    total_by_role: any;
    active_vs_inactive: any;
    recent_registrations: any;
  };
  filters_applied: any;
}

@Injectable({
  providedIn: 'root'
})
export class SuperAdminService {
  // ✅ FIXED: environment.apiUrl already includes /api, so don't add it again
  private apiUrl = `${environment.apiUrl}/superadmin`;

  constructor(private http: HttpClient) {}

  /**
   * Get JWT token from localStorage
   */
  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('authToken');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }

  // ===================================
  // ENHANCED DASHBOARD & ANALYTICS
  // ===================================

  /**
   * Get enhanced SuperAdmin dashboard statistics with AI service status
   */
  getDashboardStats(): Observable<DashboardStats> {
    const token = localStorage.getItem('authToken');
    console.log('🔐 SuperAdmin Service - Checking auth token:', token ? 'Token found' : 'No token');
    console.log('🔗 SuperAdmin Service - Dashboard URL:', `${this.apiUrl}/dashboard`);
    
    return this.http.get<DashboardStats>(`${this.apiUrl}/dashboard`, {
      headers: this.getAuthHeaders()
    }).pipe(
      tap(response => {
        console.log('✅ SuperAdmin dashboard response:', response);
      }),
      catchError((error) => {
        console.error('❌ SuperAdmin dashboard error details:', error);
        console.error('❌ Error status:', error.status);
        console.error('❌ Error message:', error.message);
        console.error('❌ Error body:', error.error);
        return this.handleError(error);
      })
    );
  }

  /**
   * Get enhanced aggregated analytics with AI insights
   */
  getAggregatedAnalytics(days: number = 30): Observable<EnhancedAnalyticsData> {
    return this.http.get<EnhancedAnalyticsData>(`${this.apiUrl}/analytics/aggregated?days=${days}`, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  // ===================================
  // ENHANCED UNIVERSITY MANAGEMENT
  // ===================================

  /**
   * Get all universities with enhanced AI capabilities and branding status
   */
  getUniversities(): Observable<any> {
    return this.http.get(`${this.apiUrl}/universities`, {
      headers: this.getAuthHeaders()
    }).pipe(
      tap(response => {
        console.log('✅ SuperAdmin universities response:', response);
      }),
      catchError(this.handleError)
    );
  }

  /**
   * Legacy method for backward compatibility
   */
  getAllUniversities(): Observable<any> {
    return this.getUniversities();
  }

  /**
   * Get comprehensive university details with AI analytics and branding analysis
   */
  getUniversityDetails(xId: string): Observable<UniversityDetails> {
    return this.http.get<UniversityDetails>(`${this.apiUrl}/universities/${xId}`, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Update university settings including branding and AI configuration
   */
  updateUniversitySettings(xId: string, updateData: any): Observable<any> {
    return this.http.put(`${this.apiUrl}/universities/${xId}/update`, updateData, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Create new university
   */
  createUniversity(universityData: any): Observable<any> {
    return this.http.post(`${this.apiUrl.replace('/superadmin', '/university')}/create`, universityData, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  // ===================================
  // ENHANCED USER MANAGEMENT
  // ===================================

  /**
   * Get all users with enhanced filtering and analytics
   */
  getUsers(filters?: {
    role?: string;
    university_id?: string;
    university_x_id?: string;
    page?: number;
    limit?: number;
    include_inactive?: boolean;
  }): Observable<UserManagement> {
    let queryParams = '';
    if (filters) {
      queryParams = '?' + Object.keys(filters)
        .filter(key => filters[key as keyof typeof filters] !== null && filters[key as keyof typeof filters] !== undefined)
        .map(key => `${key}=${encodeURIComponent(filters[key as keyof typeof filters] as string)}`)
        .join('&');
    }

    return this.http.get<UserManagement>(`${this.apiUrl}/users${queryParams}`, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Legacy method for backward compatibility
   */
  getAllUsers(filters?: any): Observable<any> {
    return this.getUsers(filters);
  }

  /**
   * Create new admin user with enhanced validation
   */
  createAdminUser(userData: {
    email: string;
    password: string;
    university_id?: string;
    university_x_id?: string;
    first_name?: string;
    last_name?: string;
    phone?: string;
    timezone?: string;
  }): Observable<any> {
    return this.http.post(`${this.apiUrl}/users/create-admin`, userData, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Legacy method for backward compatibility
   */
  createUser(userData: any): Observable<any> {
    return this.createAdminUser(userData);
  }

  /**
   * Update user - placeholder for backward compatibility
   */
  updateUser(userId: string, userData: any): Observable<any> {
    // This would need to be implemented in the backend
    return this.http.put(`${this.apiUrl}/users/${userId}`, userData, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Delete user - placeholder for backward compatibility
   */
  deleteUser(userId: string, method: 'soft' | 'hard' = 'soft'): Observable<any> {
    return this.http.delete(`${this.apiUrl}/users/${userId}?method=${method}`, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Reactivate user - placeholder for backward compatibility
   */
  reactivateUser(userId: string): Observable<any> {
    return this.http.put(`${this.apiUrl}/users/${userId}/reactivate`, {}, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  // ===================================
  // SYSTEM HEALTH & MONITORING
  // ===================================

  /**
   * Get comprehensive system health status
   */
  getSystemHealth(): Observable<SystemHealthStatus> {
    return this.http.get<SystemHealthStatus>(`${this.apiUrl}/system/health`, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Trigger system maintenance tasks
   */
  triggerMaintenanceTask(taskType: 'cleanup_sessions' | 'rebuild_indexes' | 'sync_university_data' | 'cleanup_cache'): Observable<any> {
    return this.http.post(`${this.apiUrl}/system/maintenance`, { task_type: taskType }, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  // ===================================
  // ENHANCED AUDIT & LOGGING
  // ===================================

  /**
   * Get enhanced audit logs with filtering and analytics
   */
  getAuditLogs(filters?: {
    limit?: number;
    university?: string;
    action?: string;
    user?: string;
    date_from?: string;
    date_to?: string;
  }): Observable<any> {
    let queryParams = '';
    if (filters) {
      queryParams = '?' + Object.keys(filters)
        .filter(key => filters[key as keyof typeof filters] !== null && filters[key as keyof typeof filters] !== undefined)
        .map(key => `${key}=${encodeURIComponent(filters[key as keyof typeof filters] as string)}`)
        .join('&');
    }

    return this.http.get(`${this.apiUrl}/audit-logs${queryParams}`, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  // ===================================
  // DOCUMENT & AI MANAGEMENT
  // ===================================

  /**
   * Get document processing analytics across all universities
   */
  getDocumentAnalytics(): Observable<any> {
    return this.getAggregatedAnalytics(30).pipe(
      map(analytics => ({
        success: true,
        document_analytics: analytics.analytics.ai_services,
        insights: {
          total_universities: analytics.analytics.ai_services.total_universities,
          ai_coverage_percentage: analytics.analytics.ai_services.ai_enabled_universities / analytics.analytics.ai_services.total_universities * 100,
          document_distribution: analytics.analytics.ai_services.document_distribution || [],
          recommendations: analytics.analytics.insights.recommendations.filter((rec: any) => 
            rec.category === 'ai_setup' || rec.category === 'ai_services'
          )
        }
      }))
    );
  }

  /**
   * Get AI services status across all universities
   */
  getAIServicesStatus(): Observable<any> {
    return this.getSystemHealth().pipe(
      map(health => ({
        success: true,
        ai_services_status: {
          overall_health: health.overall_health,
          enhanced_rag: health.ai_services?.enhanced_rag || { status: 'unavailable' },
          pdf_processing: health.ai_services?.pdf_processing || { status: 'unavailable' },
          universities_coverage: health.performance_metrics?.ai_coverage_percentage || 0,
          recommendations: health.recommendations.filter(rec => rec.category === 'ai_services' || rec.category === 'ai_setup')
        }
      }))
    );
  }

  /**
   * Rebuild FAISS index for a specific university
   */
  rebuildUniversityIndex(universityXId: string): Observable<any> {
    return this.http.post(`${environment.apiUrl}/university/${universityXId}/rebuild-index`, {}, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get university-specific document analytics
   */
  getUniversityDocumentAnalytics(universityXId: string): Observable<any> {
    return this.getUniversityDetails(universityXId).pipe(
      map(details => ({
        success: true,
        university_x_id: universityXId,
        document_analytics: details.university.document_analytics,
        ai_analytics: details.university.ai_analytics,
        branding_analysis: details.university.branding_analysis
      }))
    );
  }

  // ===================================
  // ENHANCED ANALYTICS HELPERS
  // ===================================

  /**
   * Get universities performance comparison
   */
  getUniversitiesComparison(metric: 'leads' | 'sessions' | 'engagement' | 'ai_readiness' = 'leads'): Observable<any> {
    return this.getAggregatedAnalytics(30).pipe(
      map(analytics => {
        let comparisonData: any[] = [];
        
        switch (metric) {
          case 'leads':
            comparisonData = analytics.analytics.leads.leads_by_university;
            break;
          case 'sessions':
            comparisonData = analytics.analytics.sessions.sessions_by_university;
            break;
          case 'engagement':
            comparisonData = analytics.analytics.sessions.engagement_metrics;
            break;
          case 'ai_readiness':
            comparisonData = analytics.analytics.ai_services.document_distribution || [];
            break;
        }

        return {
          success: true,
          metric,
          comparison_data: comparisonData,
          insights: analytics.analytics.insights,
          generated_at: analytics.generated_at
        };
      })
    );
  }

  /**
   * Get system performance trends
   */
  getPerformanceTrends(days: number = 30): Observable<any> {
    return this.getAggregatedAnalytics(days).pipe(
      map(analytics => ({
        success: true,
        trends: {
          leads: {
            growth_rate: this.calculateGrowthRate(analytics.analytics.leads.conversion_trends),
            total_leads: analytics.analytics.leads.total_leads,
            recent_leads: analytics.analytics.leads.recent_leads
          },
          sessions: {
            total_sessions: analytics.analytics.sessions.total_sessions,
            active_sessions: analytics.analytics.sessions.active_sessions,
            avg_engagement: this.calculateAverageEngagement(analytics.analytics.sessions.engagement_metrics)
          },
          ai_adoption: {
            coverage_percentage: (analytics.analytics.ai_services.ai_enabled_universities / analytics.analytics.ai_services.total_universities) * 100,
            universities_with_ai: analytics.analytics.ai_services.ai_enabled_universities,
            total_documents: analytics.analytics.ai_services.total_documents
          }
        },
        recommendations: analytics.analytics.insights.recommendations,
        period: `${days} days`
      }))
    );
  }

  // ===================================
  // UTILITY METHODS
  // ===================================

  private calculateGrowthRate(trends: any[]): number {
    if (!trends || trends.length < 2) return 0;
    const recent = trends[trends.length - 1]?.count || 0;
    const previous = trends[trends.length - 2]?.count || 0;
    return previous === 0 ? 0 : ((recent - previous) / previous) * 100;
  }

  private calculateAverageEngagement(metrics: any[]): number {
    if (!metrics || metrics.length === 0) return 0;
    const totalEngagement = metrics.reduce((sum, metric) => sum + (metric.engagement_score || 0), 0);
    return totalEngagement / metrics.length;
  }

  /**
   * Handle HTTP errors
   */
  private handleError(error: any): Observable<never> {
    console.error('SuperAdmin Service Error:', error);
    
    // Handle specific error cases
    if (error.status === 401) {
      console.error('❌ Unauthorized - redirecting to login');
      // Handle unauthorized access
      localStorage.removeItem('authToken');
      localStorage.removeItem('currentUser');
    } else if (error.status === 403) {
      console.error('❌ Forbidden - insufficient permissions');
    } else if (error.status === 0) {
      console.error('❌ Network error - check backend connection');
    }
    
    return throwError(() => error);
  }

  // ===================================
  // LEGACY METHODS (MAINTAINED FOR COMPATIBILITY)
  // ===================================

  /**
   * Legacy analytics method for backward compatibility
   */
  getAnalytics(): Observable<AnalyticsData> {
    return this.getAggregatedAnalytics(30).pipe(
      map(enhanced => ({
        success: enhanced.success,
        data: {
          leads: {
            total: enhanced.analytics.leads.total_leads,
            recent: enhanced.analytics.leads.recent_leads,
            by_university: enhanced.analytics.leads.leads_by_university.map(item => ({
              _id: item._id,
              count: item.count,
              university_name: item._id // Fallback if university_name not available
            })),
            by_country: enhanced.analytics.leads.leads_by_country
          },
          sessions: {
            total: enhanced.analytics.sessions.total_sessions,
            active: enhanced.analytics.sessions.active_sessions,
            recent: enhanced.analytics.sessions.recent_sessions,
            by_university: enhanced.analytics.sessions.sessions_by_university.map(item => ({
              _id: item._id,
              count: item.count,
              avg_messages: item.avg_messages,
              university_name: item._id // Fallback if university_name not available
            }))
          },
          users: {
            total: enhanced.analytics.leads.total_leads, // Approximation
            by_university: enhanced.analytics.leads.leads_by_university.map(item => ({
              _id: item._id,
              total_users: item.count,
              admins: 0, // Would need separate data
              students: item.count,
              university_name: item._id
            }))
          }
        },
        timestamp: enhanced.generated_at
      }))
    );
  }

  /**
   * Legacy create university method
   */
  createNewUniversity(name: string, code: string, description: string = ''): Observable<any> {
    return this.createUniversity({ name, code, description });
  }
}