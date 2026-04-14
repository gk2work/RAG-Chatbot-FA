// universities.component.ts
import { Component, OnInit, Input, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, } from '@angular/forms';
import { AdminService } from '../../../services/admin.service';
import { Subscription } from 'rxjs';
import { PdfUploadComponent } from '../../../shared/pdf-upload/pdf-upload.component';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { AdminDocumentManagementComponent } from '../document-management/admin-document-management.component';

export interface EnhancedUniversity {
  _id: string;
  name: string;
  code: string;
  x_id: string;
  description?: string;
  document_count: number;
  created_at: string;
  
  // Enhanced analytics
  stats?: {
    total_leads?: number;
    total_sessions?: number;
    active_sessions?: number;
    total_documents?: number;
    total_chunks?: number;
  };
  
  // AI capabilities
  ai_analytics?: {
    vector_search_enabled: boolean;
    enhanced_documents: number;
    legacy_documents: number;
    ai_ready: boolean;
    processing_method: 'enhanced' | 'legacy';
    health_status: any;
  };
  
  // Document analytics
  document_analytics?: {
    total_chunks: number;
    documents_by_type: Array<{_id: string, count: number}>;
    recent_uploads: Array<any>;
    vector_search_enabled: boolean;
    last_processed: string;
  };
  
  // Branding info
  branding?: {
    completeness_score: number;
    logo_url?: string;
    theme_colors?: any;
  };
}

export interface UniversityFilters {
  search: string;
  aiStatus: 'all' | 'ai_ready' | 'needs_setup';
  documentStatus: 'all' | 'has_documents' | 'no_documents';
  sortBy: 'name' | 'created_at' | 'document_count' | 'ai_score';
  sortOrder: 'asc' | 'desc';
}

@Component({
  selector: 'app-universities',
  standalone: true,
  imports: [CommonModule, FormsModule, PdfUploadComponent, MatDialogModule, MatButtonModule, MatIconModule],
  templateUrl:'./universities.component.html', 
  styleUrls: ['./universities.component.scss']
})
export class UniversitiesComponent implements OnInit, OnDestroy {
  @Input() adminUniversityContext: any = null;
  @Input() universities: EnhancedUniversity[] = []; // Added to fix binding error
  @Input() leads: any[] = []; // Added to fix binding error
  @Input() chatSessions: any[] = []; // Added to fix binding error

  // Data - now using internal arrays that can be overridden by inputs
  internalUniversities: EnhancedUniversity[] = [];
  filteredUniversities: EnhancedUniversity[] = [];
  selectedUniversity: EnhancedUniversity | null = null;

  // UI State
  loading = false;
  showDocumentManager = false;
  showAnalyticsModal = false;

  // Filters
  filters: UniversityFilters = {
    search: '',
    aiStatus: 'all',
    documentStatus: 'all',
    sortBy: 'name',
    sortOrder: 'asc'
  };

  private subscriptions: Subscription[] = [];

  constructor(private adminService: AdminService,
              private dialog: MatDialog
  ) {}

  ngOnInit() {
    // Use input universities if provided, otherwise load from service
    if (this.universities && this.universities.length > 0) {
      this.internalUniversities = this.universities;
      this.applyFilters();
    } else {
      this.loadUniversities();
    }
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

 loadUniversities() {
  this.loading = true;
  
  // Get admin's university context
  const adminContext = JSON.parse(localStorage.getItem('adminUniversityContext') || 'null');
  
  if (!adminContext || !adminContext.x_id) {
    console.error('❌ No admin university context found');
    this.loading = false;
    return;
  }

  console.log('🏛️ Loading data for admin university:', adminContext);

  // Load only the admin's assigned university
  const universitySub = this.adminService.getUniversity(adminContext.x_id).subscribe({
    next: (response) => {
      // Convert single university to array format for existing template
      const singleUniversity = response.university;
      this.internalUniversities = this.enhanceUniversityData([singleUniversity]);
      this.applyFilters();
      this.loading = false;
      console.log('✅ Loaded admin university data:', singleUniversity);
    },
    error: (error) => {
      console.error('❌ Error loading admin university:', error);
      this.loading = false;
    }
  });
  
  this.subscriptions.push(universitySub);
}

private getAdminUniversityContext() {
  const context = localStorage.getItem('adminUniversityContext');
  return context ? JSON.parse(context) : null;
}

  private enhanceUniversityData(universities: any[]): EnhancedUniversity[] {
    return universities.map(uni => ({
      ...uni,
      // Add default values for enhanced analytics
      ai_analytics: uni.ai_analytics || {
        vector_search_enabled: false,
        enhanced_documents: 0,
        legacy_documents: uni.document_count || 0,
        ai_ready: false,
        processing_method: 'legacy',
        health_status: { healthy: false }
      },
      stats: uni.stats || {
        total_documents: uni.document_count || 0,
        total_chunks: 0,
        total_leads: 0,
        total_sessions: 0
      }
    }));
  }

  applyFilters() {
    let filtered = [...this.internalUniversities];

    // Search filter
    if (this.filters.search.trim()) {
      const searchTerm = this.filters.search.toLowerCase();
      filtered = filtered.filter(uni => 
        uni.name.toLowerCase().includes(searchTerm) ||
        uni.code.toLowerCase().includes(searchTerm) ||
        uni.x_id.toLowerCase().includes(searchTerm)
      );
    }

    // AI Status filter
    if (this.filters.aiStatus !== 'all') {
      filtered = filtered.filter(uni => {
        const isAIReady = uni.ai_analytics?.ai_ready;
        return this.filters.aiStatus === 'ai_ready' ? isAIReady : !isAIReady;
      });
    }

    // Document Status filter
    if (this.filters.documentStatus !== 'all') {
      filtered = filtered.filter(uni => {
        const hasDocuments = (uni.stats?.total_documents || 0) > 0;
        return this.filters.documentStatus === 'has_documents' ? hasDocuments : !hasDocuments;
      });
    }

    // Sorting
    filtered.sort((a, b) => {
      let valueA: any, valueB: any;
      
      switch (this.filters.sortBy) {
        case 'name':
          valueA = a.name.toLowerCase();
          valueB = b.name.toLowerCase();
          break;
        case 'created_at':
          valueA = new Date(a.created_at).getTime();
          valueB = new Date(b.created_at).getTime();
          break;
        case 'document_count':
          valueA = a.stats?.total_documents || 0;
          valueB = b.stats?.total_documents || 0;
          break;
        case 'ai_score':
          valueA = this.getAIReadinessScore(a);
          valueB = this.getAIReadinessScore(b);
          break;
        default:
          valueA = a.name.toLowerCase();
          valueB = b.name.toLowerCase();
      }

      if (valueA < valueB) return this.filters.sortOrder === 'asc' ? -1 : 1;
      if (valueA > valueB) return this.filters.sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    this.filteredUniversities = filtered;
  }

  toggleSortOrder() {
    this.filters.sortOrder = this.filters.sortOrder === 'asc' ? 'desc' : 'asc';
    this.applyFilters();
  }

  selectUniversity(university: EnhancedUniversity) {
    this.selectedUniversity = university;
  }

openDocumentManager(university: EnhancedUniversity) {
  console.log('📚 Opening document manager for:', university);
  
  const dialogRef = this.dialog.open(AdminDocumentManagementComponent, {
    width: '1000px',
    maxWidth: '95vw',
    height: '80vh',
    disableClose: false,
    data: { 
      university,
      adminMode: true, // Admin mode
      universityContext: {
        x_id: university.x_id,
        code: university.code,
        name: university.name
      }
    }
  });

  dialogRef.afterClosed().subscribe(result => {
    if (result?.success) {
      console.log('✅ Document management completed:', result);
      // Refresh university data to show updated document count
      this.loadUniversities();
    }
  });
}

  closeDocumentManager() {
    this.showDocumentManager = false;
    this.selectedUniversity = null;
  }

  viewAnalytics(university: EnhancedUniversity) {
    // Implement analytics modal or navigation
    console.log('Viewing analytics for:', university);
  }

  refreshUniversities() {
    this.loadUniversities();
  }

  // Event Handlers
  onDocumentUploaded(document: any) {
    console.log('Document uploaded:', document);
    // Optionally refresh university data
    this.loadUniversities();
  }

  onDocumentsChanged(documents: any[]) {
    console.log('Documents changed:', documents);
    // Update the selected university's document count
    if (this.selectedUniversity) {
      this.selectedUniversity.stats!.total_documents = documents.length;
    }
  }

  // Utility Methods
  getAIReadinessScore(university: EnhancedUniversity): number {
    if (!university.ai_analytics) return 0;
    
    let score = 0;
    
    // Vector search capability (30 points)
    if (university.ai_analytics.vector_search_enabled) score += 30;
    
    // Document processing (40 points)
    if (university.ai_analytics.enhanced_documents > 0) score += 20;
    if ((university.stats?.total_chunks || 0) > 0) score += 20;
    
    // System health (30 points)
    if (university.ai_analytics.health_status?.healthy) score += 30;
    
    return Math.min(100, score);
  }

  getReadinessClass(university: EnhancedUniversity): string {
    const score = this.getAIReadinessScore(university);
    if (score >= 80) return 'high';
    if (score >= 50) return 'medium';
    return 'low';
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString();
  }

  trackUniversity(index: number, university: EnhancedUniversity): string {
    return university.x_id;
  }
  // Add these missing methods
  getUniversityLeadCount(code: string): number {
    return this.leads.filter(lead => lead.university_code === code).length;
  }

  getUniversitySessionCount(code: string): number {
    return this.chatSessions.filter(session => session.university_code === code).length;
  }

  onManageDocuments(university: EnhancedUniversity) {
    this.openDocumentManager(university);
  }

  onLoadStats(university: EnhancedUniversity) {
    this.viewAnalytics(university);
  }
}
