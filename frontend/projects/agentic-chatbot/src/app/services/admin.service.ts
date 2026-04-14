// admin.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpEventType, HttpRequest, HttpParams } from '@angular/common/http';
import { Observable, forkJoin, Subject, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';


export interface PDFUploadProgress {
  progress: number;
  file: File;
  status: "uploading" | "completed" | "error";
  result?: any;
  error?: string;
}

export interface DocumentAnalytics {
  total_chunks: number;
  documents_by_type: Array<{_id: string, chunk_count: number}>;
  recent_uploads: Array<{metadata: any, created_at: string}>;
  vector_search_enabled: boolean;
  ai_ready: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  // ✅ FIXED: environment.apiUrl already includes /api, so don't add it again  
  private baseUrl = `${environment.apiUrl}`;
  private uploadProgress$ = new Subject<PDFUploadProgress>();

  constructor(private http: HttpClient) {}

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('authToken');
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    });
  }

  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('authToken');
    const headers = new HttpHeaders();
    return token ? headers.set('Authorization', `Bearer ${token}`) : headers;
  }

  
  uploadPDFDocument(universityXId: string, file: File, title?: string): Observable<PDFUploadProgress> {
    // Convert file to base64 for JSON API
    return new Observable(observer => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64Content = (reader.result as string).split(',')[1]; // Remove data:application/pdf;base64, prefix
        
        const documentData = {
          title: title || file.name,
          content: base64Content,
          type: 'pdf',
          metadata: {
            source_file: file.name,
            upload_method: 'admin_portal',
            file_size: file.size
          }
        };

        // Send upload progress
        observer.next({
          progress: 10,
          file,
          status: 'uploading'
        });

        this.http.post(`${this.baseUrl}/university/${universityXId}/documents`, documentData, {
          headers: this.getHeaders()
        }).subscribe({
          next: (response: any) => {
            observer.next({
              progress: 100,
              file,
              status: 'completed',
              result: response
            });
            observer.complete();
          },
          error: (error) => {
            observer.next({
              progress: 0,
              file,
              status: 'error',
              error: error.error?.error || 'Upload failed'
            });
            observer.error(error);
          }
        });
      };

      reader.onerror = () => {
        observer.next({
          progress: 0,
          file,
          status: 'error',
          error: 'Failed to read file'
        });
        observer.error(new Error('Failed to read file'));
      };

      reader.readAsDataURL(file);
    });
  }

  uploadTextDocument(universityXId: string, title: string, content: string, type: string = 'text'): Observable<any> {
    const documentData = {
      title,
      content,
      type,
      metadata: {
        upload_method: 'admin_portal',
        content_length: content.length
      }
    };

    return this.http.post(`${this.baseUrl}/university/${universityXId}/documents`, documentData, {
      headers: this.getHeaders()
    });
  }

  getEnhancedUniversityDocuments(universityXId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/university/${universityXId}/documents`, {
      headers: this.getHeaders()
    });
  }

  searchUniversityDocuments(universityXId: string, query: string, searchType: string = 'hybrid'): Observable<any> {
    const searchData = { query, search_type: searchType };
    return this.http.post(`${this.baseUrl}/university/${universityXId}/search-documents`, searchData, {
      headers: this.getHeaders()
    });
  }

  rebuildUniversityIndex(universityXId: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/university/${universityXId}/rebuild-index`, {}, {
      headers: this.getHeaders()
    });
  }

  getUniversityHealthCheck(universityXId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/university/${universityXId}/health`, {
      headers: this.getHeaders()
    });
  }

  deleteDocument(universityXId: string, documentId: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/university/${universityXId}/documents/${documentId}`, {
      headers: this.getHeaders()
    });
  }

  getUploadProgress(): Observable<PDFUploadProgress> {
    return this.uploadProgress$.asObservable();
  }

  validatePDFFile(file: File): { valid: boolean; error?: string } {
    // Check file type
    if (file.type !== 'application/pdf') {
      return {
        valid: false,
        error: 'Only PDF files are allowed'
      };
    }

    // Check file size (10MB max for PDFs)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      return { 
        valid: false, 
        error: 'PDF file size must be less than 10MB' 
      };
    }

    return { valid: true };
  }

  getLeads(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/lead/get-leads`, {
      headers: this.getHeaders()  // ✅ Includes JWT token
    });
  }

  getLead(leadId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/lead/get-lead/${leadId}`, {
      headers: this.getHeaders() // ✅ Added auth headers
    });
  }

  getLeadChatSummaries(leadId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/lead/get-lead/${leadId}`, {
      headers: this.getHeaders() // ✅ Added auth headers
    }).pipe(
      map((response: any) => response.lead?.live_chat_summaries || [])
    );
  }

  getUniversityLeadAnalytics(universityXId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/lead/analytics/${universityXId}`, {
      headers: this.getHeaders()
    });
  }

  getLeadsByUniversity(universityXId: string, filters?: any): Observable<any> {
    let queryParams = '';
    if (filters) {
      queryParams = '?' + Object.keys(filters)
        .filter(key => filters[key] !== null && filters[key] !== undefined)
        .map(key => `${key}=${encodeURIComponent(filters[key])}`)
        .join('&');
    }
    
    return this.http.get(`${this.baseUrl}/lead/by-university/${universityXId}${queryParams}`, {
      headers: this.getHeaders()
    });
  }

  getLeadConversationInsights(leadId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/lead/conversation-insights/${leadId}`, {
      headers: this.getHeaders()
    });
  }

  getUniversities(): Observable<any> {
    return this.http.get(`${this.baseUrl}/university/list`, {
      headers: this.getHeaders() // ✅ Added auth headers
    });
  }

  getUniversity(xId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/university/${xId}`, {
      headers: this.getHeaders() // ✅ Added auth headers
    });
  }

  getUniversityStats(xId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/university/${xId}/stats`, {
      headers: this.getHeaders() // ✅ Added auth headers
    });
  }

  getUniversityDocuments(xId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/university/${xId}/documents`, {
      headers: this.getHeaders() // ✅ Added auth headers
    });
  }

  getAllChatSessions(): Observable<any> {
    // Use the sessions from leads since there's no direct "all sessions" endpoint
    return this.getSessionsFromLeads();
  }

  getChatHistory(sessionId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/chat/history/${sessionId}`, {
      headers: this.getHeaders() // ✅ Already has auth headers
    });
  }

  getUserSessions(userId: string, limit: number = 50): Observable<any> {
    return this.http.get(`${this.baseUrl}/chat/sessions/user/${userId}?limit=${limit}`, {
      headers: this.getHeaders() // ✅ Already has auth headers
    });
  }

  getUniversitySessions(universityIdentifier: string, limit: number = 50): Observable<any> {
    return this.http.get(`${this.baseUrl}/chat/sessions/university/${universityIdentifier}?limit=${limit}`, {
      headers: this.getHeaders() // ✅ Already has auth headers
    });
  }

  getSessionSummary(sessionId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/chat/session/${sessionId}/summary`, {
      headers: this.getHeaders() // ✅ Already has auth headers
    });
  }

  private getSessionsFromLeads(): Observable<any> {
    return this.getLeads().pipe(
      map((leadsResponse: any) => {
        const leads = leadsResponse.leads || [];
        const sessions: any[] = [];
        
        leads.forEach((lead: any) => {
          if (lead.live_chat_summaries) {
            lead.live_chat_summaries.forEach((summary: any) => {
              sessions.push({
                _id: summary.session_id,
                lead_id: lead._id,
                lead_name: lead.name,
                lead_email: lead.email,
                university_code: lead.university_code,
                university_x_id: lead.university_x_id,
                messages: [], // Would need separate call to get actual messages
                message_count: 0,
                created_at: summary.timestamp,
                is_active: false,
                topics: summary.metadata?.topics || []
              });
            });
          }
        });
        
        return { sessions, success: true };
      })
    );
  }

  getUniversityAnalytics(universityXId: string, dateRange?: { start: string, end: string }): Observable<any> {
    let queryParams = '';
    if (dateRange) {
      queryParams = `?start_date=${dateRange.start}&end_date=${dateRange.end}`;
    }
    
    return forkJoin({
      stats: this.getUniversityStats(universityXId),
      leadAnalytics: this.getUniversityLeadAnalytics(universityXId),
      documents: this.getEnhancedUniversityDocuments(universityXId),
      health: this.getUniversityHealthCheck(universityXId)
    }).pipe(
      map(results => ({
        success: true,
        analytics: {
          overview: results.stats,
          leads: results.leadAnalytics,
          documents: results.documents,
          system_health: results.health,
          generated_at: new Date().toISOString()
        }
      }))
    );
  }

  getUniversityAIStatus(universityXId: string): Observable<any> {
    return this.getUniversityHealthCheck(universityXId).pipe(
      map((health: any) => ({
        ai_enabled: health.components?.enhanced_rag?.healthy || false,
        vector_search_available: health.capabilities?.vector_search_enabled || false,
        document_processing_ready: health.capabilities?.document_processing_available || false,
        enhancement_recommendations: health.recommendations || []
      }))
    );
  }

  private handleError(error: any): Observable<never> {
    console.error('AdminService error:', error);
    throw error;
  }

updateLeadCategorization(leadId: string, leadType: string, notes?: string): Observable<any> {
  const body = {
    lead_type: leadType,
    notes: notes || ''
  };

  return this.http.put(`${this.baseUrl}/lead/leads/${leadId}/categorize`, body, {
    headers: this.getAuthHeaders()
  });
}
 
getCategorizationStats(): Observable<any> {
  return this.http.get(`${this.baseUrl}/lead/dashboard/categorization-stats`, {
    headers: this.getAuthHeaders()
  });
}

getLeadsByCategory(category: string, limit: number = 50): Observable<any> {
  const params = new HttpParams()
    .set('category', category)
    .set('limit', limit.toString());

  return this.http.get(`${this.baseUrl}/lead/leads/by-category`, {
    headers: this.getAuthHeaders(),
    params: params
  });
}

/**
   * Get session trends data for dashboard charts
   */
  getSessionTrends(timeRange: 'week' | 'month' | 'quarter' = 'week'): Observable<any> {
    const params = new HttpParams().set('range', timeRange);

    return this.http.get(`${this.baseUrl}/lead/dashboard/session-trends`, {
      headers: this.getAuthHeaders(),
      params: params
    });
  }

  /**
   * Get enhanced dashboard metrics
   */
  getEnhancedMetrics(): Observable<any> {
    return this.http.get(`${this.baseUrl}/lead/dashboard/enhanced-metrics`, {
      headers: this.getAuthHeaders()
    });
  }

  /**
   * Get comprehensive dashboard analytics (combines multiple calls)
   */
  getDashboardAnalytics(timeRange: 'week' | 'month' | 'quarter' = 'week'): Observable<any> {
    return forkJoin({
      categorization: this.getCategorizationStats(),
      trends: this.getSessionTrends(timeRange),
      metrics: this.getEnhancedMetrics()
    }).pipe(
      map(results => ({
        success: true,
        analytics: {
          categorization_stats: results.categorization.categorization_stats,
          session_trends: results.trends.session_trends,
          enhanced_metrics: results.metrics.enhanced_metrics,
          time_range: timeRange,
          generated_at: new Date().toISOString()
        }
      })),
      catchError(error => {
        console.error('Error getting dashboard analytics:', error);
        return of({
          success: false,
          error: 'Failed to load dashboard analytics'
        });
      })
    );
  }

  /**
   * Get session analytics for a specific time period
   */
  getSessionAnalyticsByPeriod(
    startDate: string, 
    endDate: string, 
    universityXId?: string
  ): Observable<any> {
    let params = new HttpParams()
      .set('start_date', startDate)
      .set('end_date', endDate);

    if (universityXId) {
      params = params.set('university_x_id', universityXId);
    }

    return this.http.get(`${this.baseUrl}/lead/dashboard/session-analytics`, {
      headers: this.getAuthHeaders(),
      params: params
    });
  }

  /**
   * Get real-time session metrics (for live dashboard updates)
   */
  getRealTimeMetrics(): Observable<any> {
    return this.http.get(`${this.baseUrl}/lead/dashboard/realtime-metrics`, {
      headers: this.getAuthHeaders()
    });
  }

  /**
   * Get session engagement metrics
   */
  getEngagementMetrics(period: string = 'week'): Observable<any> {
    const params = new HttpParams().set('period', period);

    return this.http.get(`${this.baseUrl}/lead/dashboard/engagement-metrics`, {
      headers: this.getAuthHeaders(),
      params: params
    });
  }

  /**
   * Get user behavior analytics
   */
  getUserBehaviorAnalytics(): Observable<any> {
    return this.http.get(`${this.baseUrl}/lead/dashboard/user-behavior`, {
      headers: this.getAuthHeaders()
    });
  }

  // Enhanced session management methods

  /**
   * Get detailed session analytics for admin portal
   */
  getDetailedSessionAnalytics(limit: number = 100): Observable<any> {
    const params = new HttpParams().set('limit', limit.toString());

    return this.http.get(`${this.baseUrl}/chat/sessions/detailed-analytics`, {
      headers: this.getAuthHeaders(),
      params: params
    });
  }

  /**
   * Get session performance metrics
   */
  getSessionPerformanceMetrics(): Observable<any> {
    return this.http.get(`${this.baseUrl}/chat/sessions/performance-metrics`, {
      headers: this.getAuthHeaders()
    });
  }

  /**
   * Get session trends with custom date range
   */
  getCustomSessionTrends(startDate: Date, endDate: Date): Observable<any> {
    const params = new HttpParams()
      .set('start_date', startDate.toISOString())
      .set('end_date', endDate.toISOString());

    return this.http.get(`${this.baseUrl}/lead/dashboard/custom-trends`, {
      headers: this.getAuthHeaders(),
      params: params
    });
  }

  /**
   * Refresh dashboard cache (for real-time updates)
   */
  refreshDashboardCache(): Observable<any> {
    return this.http.post(`${this.baseUrl}/dashboard/refresh-cache`, {}, {
      headers: this.getAuthHeaders()
    });
  }

  // Helper methods for dashboard data processing

  /**
   * Process session trends data for charts
   */
  private processSessionTrendsForCharts(rawData: any): any {
    if (!rawData?.session_trends) {
      return {
        labels: [],
        datasets: []
      };
    }

    const trends = rawData.session_trends;
    return {
      labels: trends.dates || [],
      datasets: [
        {
          label: 'Sessions',
          data: trends.session_counts || [],
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          tension: 0.4
        },
        {
          label: 'Messages',
          data: trends.message_counts || [],
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          tension: 0.4
        }
      ]
    };
  }

  /**
   * Calculate percentage change between periods
   */
  calculatePercentageChange(current: number, previous: number): number {
    if (previous === 0) {
      return current > 0 ? 100 : 0;
    }
    return Math.round(((current - previous) / previous) * 100);
  }

  /**
   * Format duration for display
   */
  formatDuration(minutes: number): string {
    if (minutes < 1) {
      return '< 1 min';
    } else if (minutes < 60) {
      return `${Math.round(minutes)} min`;
    } else {
      const hours = Math.floor(minutes / 60);
      const remainingMinutes = Math.round(minutes % 60);
      return `${hours}h ${remainingMinutes}m`;
    }
  }
}