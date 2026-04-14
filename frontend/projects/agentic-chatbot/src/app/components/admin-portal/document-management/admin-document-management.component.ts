// admin-document-management.component.ts - COMPLETE FIXED VERSION
import { Component, OnInit, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { FormsModule } from '@angular/forms';
import { PdfUploadComponent } from '../../../shared/pdf-upload/pdf-upload.component';
import { PdfUploadService } from '../../../services/pdf-upload.service';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';

interface UniversityContext {
  x_id: string;
  code: string;
  name?: string;
}

interface DocumentSearchResult {
  chunk_id: number;
  text: string;
  similarity_score?: number;
  metadata: {
    source_file: string;
    chunk_size: number;
    total_chunks: number;
  };
}

@Component({
  selector: 'app-admin-document-management',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatDialogModule,
    FormsModule,
    PdfUploadComponent
  ],
  templateUrl: './admin-document-management.component.html',
  styleUrls: ['./admin-document-management.component.scss']
})
export class AdminDocumentManagementComponent implements OnInit {
  universityContext: UniversityContext | null = null;
  activeTab = 0;
  
  // Document search
  searchQuery = '';
  searchResults: DocumentSearchResult[] = [];
  searchMethod: 'text' | 'vector' = 'vector';
  searching = false;
  
  // Upload tracking
  totalUploaded = 0;
  uploadErrors: string[] = [];
  
  // ✅ FIXED: Loading state management
  contextLoading = true;
  contextError = false;

  constructor(
    private pdfUploadService: PdfUploadService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
    @Inject(MAT_DIALOG_DATA) public data: any
  ) {}

  ngOnInit() {
    console.log('🔧 AdminDocumentManagementComponent initializing...');
    console.log('📦 Dialog data:', this.data);
    this.loadUniversityContext();
    
    // ✅ DEBUG: Timer to check final state
    setTimeout(() => {
      console.log('🔍 Final state check:');
      console.log('- contextLoading:', this.contextLoading);
      console.log('- contextError:', this.contextError);
      console.log('- universityContext:', this.universityContext);
      console.log('- canUpload:', this.canUpload);
    }, 1000);
  }

  // ✅ FIXED: Enhanced context loading with better error handling
  loadUniversityContext() {
    console.log('🔍 Loading university context...');
    this.contextLoading = true;
    this.contextError = false;

    // Method 1: Check dialog data first (SuperAdmin mode)
    if (this.data?.universityContext) {
      this.universityContext = this.data.universityContext;
      console.log('✅ Dialog Context loaded:', this.universityContext);
      this.contextLoading = false;
      return;
    }

    // Method 2: Check temp context (from university management)
    const tempContext = localStorage.getItem('tempUniversityContext');
    if (tempContext) {
      this.universityContext = JSON.parse(tempContext);
      localStorage.removeItem('tempUniversityContext');
      console.log('✅ Temp Context loaded:', this.universityContext);
      this.contextLoading = false;
      return;
    }

    // Method 3: Fallback to admin context
    const contextData = localStorage.getItem('adminUniversityContext');
    if (contextData) {
      this.universityContext = JSON.parse(contextData);
      console.log('✅ Admin Context loaded:', this.universityContext);
      this.contextLoading = false;
      return;
    }

    // No context found - show error
    console.error('❌ No university context found');
    this.contextError = true;
    this.contextLoading = false;
    this.snackBar.open('No university context found. Please refresh or contact support.', 'Close', {
      duration: 10000,
      panelClass: ['error-snackbar']
    });
  }

  // Upload Event Handlers
  onDocumentUploaded(event: any) {
    console.log('📄 Document uploaded:', event);
    this.totalUploaded++;
    
    this.snackBar.open(
      `✅ Document "${event.filename}" uploaded successfully! Total: ${this.totalUploaded}`,
      'Close',
      { duration: 4000, panelClass: ['success-snackbar'] }
    );
  }

  onUploadProgress(progress: number) {
    // Handle upload progress if needed for UI updates
    console.log('📈 Upload progress:', progress);
  }

  onUploadError(error: string) {
    console.error('❌ Upload error:', error);
    this.uploadErrors.push(error);
    
    this.snackBar.open(`Upload failed: ${error}`, 'Close', {
      duration: 6000,
      panelClass: ['error-snackbar']
    });
  }

  // Document Search
  async searchDocuments() {
    if (!this.searchQuery.trim()) {
      this.snackBar.open('Please enter a search query', 'Close', { duration: 3000 });
      return;
    }

    if (!this.universityContext?.x_id) {
      this.snackBar.open('University context not available', 'Close', { duration: 3000 });
      return;
    }

    this.searching = true;
    this.searchResults = [];

    try {
      const results = await this.pdfUploadService.searchDocuments(
        this.universityContext.x_id,
        this.searchQuery,
        this.searchMethod
      ).toPromise();

      this.searchResults = results.chunks || [];
      
      if (this.searchResults.length === 0) {
        this.snackBar.open('No results found for your query', 'Close', { duration: 3000 });
      } else {
        this.snackBar.open(
          `Found ${this.searchResults.length} relevant chunks`,
          'Close',
          { duration: 3000, panelClass: ['info-snackbar'] }
        );
      }
    } catch (error: any) {
      console.error('Search error:', error);
      this.snackBar.open(
        `Search failed: ${error.message || 'Unknown error'}`,
        'Close',
        { duration: 5000, panelClass: ['error-snackbar'] }
      );
    } finally {
      this.searching = false;
    }
  }

  clearSearch() {
    this.searchQuery = '';
    this.searchResults = [];
  }

  switchSearchMethod() {
    this.searchMethod = this.searchMethod === 'vector' ? 'text' : 'vector';
    this.snackBar.open(
      `Switched to ${this.searchMethod === 'vector' ? 'AI-powered vector' : 'traditional text'} search`,
      'Close',
      { duration: 2000 }
    );
  }

  // Utility methods
  highlightSearchTerm(text: string, query: string): string {
    if (!query.trim()) return text;
    
    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  }

  formatSimilarityScore(score: number): string {
    return `${Math.round(score * 100)}% match`;
  }

  getSearchMethodIcon(): string {
    return this.searchMethod === 'vector' ? 'psychology' : 'search';
  }

  getSearchMethodLabel(): string {
    return this.searchMethod === 'vector' ? 'AI Vector Search' : 'Text Search';
  }

  getSearchMethodDescription(): string {
    return this.searchMethod === 'vector' 
      ? 'AI-powered semantic search that understands context and meaning'
      : 'Traditional keyword-based text search';
  }

  // ✅ FIXED: Enhanced navigation helpers with better fallbacks
  get universityName(): string {
    return this.universityContext?.name || this.universityContext?.code || 'Unknown University';
  }

  get universityCode(): string {
    return this.universityContext?.code || 'N/A';
  }

  get universityXId(): string {
    return this.universityContext?.x_id || '';
  }

  // ✅ NEW: Upload validation getter
  get canUpload(): boolean {
    return !this.contextLoading && !this.contextError && !!this.universityContext?.x_id;
  }
}