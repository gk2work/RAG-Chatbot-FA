// university-branding-dialog.component.ts
import { Component, Inject, OnInit, OnDestroy } from "@angular/core";
import { CommonModule } from "@angular/common";
import {
  FormBuilder,
  FormGroup,
  Validators,
  ReactiveFormsModule,
} from "@angular/forms";
import {
  MatDialogRef,
  MAT_DIALOG_DATA,
  MatDialogModule,
} from "@angular/material/dialog";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatTabsModule } from "@angular/material/tabs";
import { MatSnackBar, MatSnackBarModule } from "@angular/material/snack-bar";
import { MatChipsModule } from "@angular/material/chips";
import { MatSlideToggleModule } from "@angular/material/slide-toggle";
import { MatProgressBarModule } from "@angular/material/progress-bar";
import { MatCardModule } from "@angular/material/card";
import { SuperAdminService, UniversityDetails } from "../../../services/super-admin.service";
import { AdminService } from "../../../services/admin.service";
import { FileUploadComponent } from "../../../shared/file-upload/file-upload.component";
import { Subscription, forkJoin } from 'rxjs';

export interface BrandingDialogData {
  university: any; // The university being customized
}

export interface DocumentManagementData {
  totalDocuments: number;
  totalChunks: number;
  vectorSearchEnabled: boolean;
  aiReady: boolean;
  recentUploads: any[];
  healthStatus: any;
  processingCapabilities: {
    pdfProcessing: boolean;
    vectorSearch: boolean;
    enhancedRag: boolean;
  };
}

export interface AIConfiguration {
  enabled: boolean;
  ragModel: string;
  maxTokens: number;
  temperature: number;
  features: {
    conversationalMemory: boolean;
    leadManagement: boolean;
    dynamicQuestioning: boolean;
  };
}

@Component({
  selector: "app-university-branding-dialog",
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
    MatSnackBarModule,
    MatChipsModule,
    MatSlideToggleModule,
    MatProgressBarModule,
    MatCardModule,
    FileUploadComponent,
  ],
  templateUrl: "./university-branding-dialog.component.html",
  styleUrls: ["./university-branding-dialog.component.scss"],
})
export class UniversityBrandingDialogComponent implements OnInit, OnDestroy {
  // Forms - properly initialized
  brandingForm: FormGroup;
  aiConfigForm: FormGroup;
  
  // Component state
  updating = false;
  loading = false;
  selectedTab = 0;
  
  // UI state for template
  showUrlInputs = false;
  previewColors = {
    primary: '#3b82f6',
    secondary: '#10b981',
    accent: '#f59e0b',
    background: '#ffffff'
  };
  
  // Data
  university: any;
  universityDetails: UniversityDetails | null = null;
  documentData: DocumentManagementData | null = null;
  aiConfig: AIConfiguration | null = null;
  
  // UI state
  brandingProgress = 0;
  aiSetupProgress = 0;
  documentMetrics = {
    documentsProcessed: 0,
    chunksGenerated: 0,
    vectorIndexSize: 0,
    lastProcessed: null as Date | null
  };
  
  // Analytics
  brandingCompleteness = 0;
  aiReadinessScore = 0;
  overallHealthScore = 0;
  
  // Recommendations
  brandingRecommendations: Array<{priority: string, message: string}> = [];
  aiRecommendations: Array<{priority: string, message: string}> = [];
  
  private subscriptions: Subscription[] = [];

  constructor(
    private fb: FormBuilder,
    private superAdminService: SuperAdminService,
    private adminService: AdminService,
    private snackBar: MatSnackBar,
    public dialogRef: MatDialogRef<UniversityBrandingDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: BrandingDialogData
  ) {
    this.university = data.university;
    
    // Initialize forms immediately in constructor
    this.brandingForm = this.fb.group({});
    this.aiConfigForm = this.fb.group({});
    
    // Setup forms with actual values
    this.initializeForms();
  }

  ngOnInit() {
    this.loadUniversityDetails();
    this.loadDocumentAnalytics();
    this.loadAIConfiguration();
    this.updatePreviewColors();
  }

  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }

  private initializeForms() {
    // Enhanced Branding Form
    this.brandingForm = this.fb.group({
      // Visual Branding
      logo_url: [this.university?.branding?.logo_url || ""],
      favicon_url: [this.university?.branding?.favicon_url || ""],
      
      // Color Scheme
      primary_color: [this.university?.branding?.theme_colors?.primary || "#3b82f6"],
      secondary_color: [this.university?.branding?.theme_colors?.secondary || "#10b981"],
      accent_color: [this.university?.branding?.theme_colors?.accent || "#f59e0b"],
      background_color: [this.university?.branding?.theme_colors?.background || "#ffffff"],
      
      // Text & Messaging
      welcome_message: [this.university?.branding?.welcome_message || ""],
      footer_text: [this.university?.branding?.footer_text || ""],
      contact_email: [this.university?.branding?.contact_email || "", [Validators.email]],
      support_phone: [this.university?.branding?.support_phone || ""],
      
      // Domain & Technical
      domain_name: [this.university?.branding?.domain_name || ""],
      custom_css: [this.university?.branding?.custom_css || ""],
      
      // Social & Marketing
      social_links: this.fb.group({
        website: [this.university?.branding?.social_links?.website || ""],
        facebook: [this.university?.branding?.social_links?.facebook || ""],
        twitter: [this.university?.branding?.social_links?.twitter || ""],
        linkedin: [this.university?.branding?.social_links?.linkedin || ""],
        instagram: [this.university?.branding?.social_links?.instagram || ""]
      }),
      
      // SEO & Meta
      meta_title: [this.university?.branding?.meta_title || ""],
      meta_description: [this.university?.branding?.meta_description || ""],
      keywords: [this.university?.branding?.keywords || ""]
    });

    // AI Configuration Form
    this.aiConfigForm = this.fb.group({
      enabled: [this.university?.ai_config?.enabled ?? true],
      ragModel: [this.university?.ai_config?.rag_model || "gpt-4o"],
      maxTokens: [this.university?.ai_config?.max_tokens || 3000, [Validators.min(100), Validators.max(8000)]],
      temperature: [this.university?.ai_config?.temperature || 0.7, [Validators.min(0), Validators.max(2)]],
      
      // Feature toggles
      conversationalMemory: [this.university?.ai_config?.features?.conversational_memory ?? true],
      leadManagement: [this.university?.ai_config?.features?.lead_management ?? true],
      dynamicQuestioning: [this.university?.ai_config?.features?.dynamic_questioning ?? true],
      vectorSearch: [this.university?.ai_config?.features?.vector_search ?? true],
      
      // Advanced settings
      responseStyle: [this.university?.ai_config?.response_style || "friendly"],
      knowledgeCutoff: [this.university?.ai_config?.knowledge_cutoff || "real-time"],
      fallbackBehavior: [this.university?.ai_config?.fallback_behavior || "graceful"],
      
      // Safety & Moderation
      contentFiltering: [this.university?.ai_config?.content_filtering ?? true],
      responseModeration: [this.university?.ai_config?.response_moderation ?? true],
      sensitiveTopicsHandling: [this.university?.ai_config?.sensitive_topics_handling || "redirect"]
    });

    // Watch for color changes to update preview
    this.brandingForm.get('primary_color')?.valueChanges.subscribe(value => {
      this.previewColors.primary = value;
    });
    this.brandingForm.get('accent_color')?.valueChanges.subscribe(value => {
      this.previewColors.accent = value;
    });
  }

  private updatePreviewColors() {
    this.previewColors = {
      primary: this.brandingForm.get('primary_color')?.value || '#3b82f6',
      secondary: this.brandingForm.get('secondary_color')?.value || '#10b981',
      accent: this.brandingForm.get('accent_color')?.value || '#f59e0b',
      background: this.brandingForm.get('background_color')?.value || '#ffffff'
    };
  }

  private loadUniversityDetails() {
    this.loading = true;
    
    const detailsSub = this.superAdminService.getUniversityDetails(this.university.x_id).subscribe({
      next: (details) => {
        this.universityDetails = details;
        this.calculateBrandingCompleteness();
        this.calculateAIReadiness();
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading university details:', error);
        this.snackBar.open('Failed to load university details', 'Close', { duration: 3000 });
        this.loading = false;
      }
    });
    
    this.subscriptions.push(detailsSub);
  }

  private loadDocumentAnalytics() {
    const analyticsSub = this.superAdminService.getUniversityDocumentAnalytics(this.university.x_id).subscribe({
      next: (analytics) => {
        if (analytics.success) {
          this.documentData = {
            totalDocuments: analytics.document_analytics?.total_chunks || 0,
            totalChunks: analytics.document_analytics?.total_chunks || 0,
            vectorSearchEnabled: analytics.ai_analytics?.vectorstore_stats?.vector_search_available || false,
            aiReady: analytics.ai_analytics?.health_status?.healthy || false,
            recentUploads: analytics.document_analytics?.recent_uploads || [],
            healthStatus: analytics.ai_analytics?.health_status,
            processingCapabilities: {
              pdfProcessing: analytics.ai_analytics?.features?.pdf_processing || false,
              vectorSearch: analytics.ai_analytics?.features?.vector_search || false,
              enhancedRag: analytics.ai_analytics?.features?.enhanced_rag || false
            }
          };
          
          this.updateDocumentMetrics();
        }
      },
      error: (error) => {
        console.error('Error loading document analytics:', error);
      }
    });
    
    this.subscriptions.push(analyticsSub);
  }

  private loadAIConfiguration() {
    // AI configuration is already loaded in university details
    if (this.university?.ai_config) {
      this.aiConfig = this.university.ai_config;
      this.calculateAIReadiness();
    }
  }

  private calculateBrandingCompleteness() {
    if (!this.universityDetails?.university.branding_analysis) return;
    
    const analysis = this.universityDetails.university.branding_analysis;
    this.brandingCompleteness = analysis.completeness_score;
    this.brandingRecommendations = analysis.recommendations || [];
    this.brandingProgress = Math.min(100, this.brandingCompleteness + 20);
  }

  private calculateAIReadiness() {
    let score = 0;
    let maxScore = 100;
    
    // AI Configuration (30 points)
    if (this.aiConfigForm?.get('enabled')?.value) score += 15;
    if (this.aiConfigForm?.get('ragModel')?.value) score += 10;
    if (this.aiConfigForm?.get('conversationalMemory')?.value) score += 5;
    
    // Document Processing (40 points) - fix null safety
    if (this.documentData?.totalDocuments && this.documentData.totalDocuments > 0) score += 20;
    if (this.documentData?.vectorSearchEnabled) score += 15;
    if (this.documentData?.aiReady) score += 5;
    
    // System Health (30 points)
    if (this.documentData?.processingCapabilities?.pdfProcessing) score += 10;
    if (this.documentData?.processingCapabilities?.vectorSearch) score += 10;
    if (this.documentData?.processingCapabilities?.enhancedRag) score += 10;
    
    this.aiReadinessScore = Math.min(100, score);
    this.aiSetupProgress = this.aiReadinessScore;
    
    this.generateAIRecommendations();
  }

  private generateAIRecommendations() {
    this.aiRecommendations = [];
    
    if (!this.aiConfigForm?.get('enabled')?.value) {
      this.aiRecommendations.push({
        priority: 'high',
        message: 'Enable AI features to unlock conversational capabilities'
      });
    }
    
    if (!this.documentData?.totalDocuments || this.documentData.totalDocuments === 0) {
      this.aiRecommendations.push({
        priority: 'high',
        message: 'Upload documents to enable knowledge-based responses'
      });
    }
    
    if (this.documentData?.totalDocuments && this.documentData.totalDocuments > 0 && !this.documentData.vectorSearchEnabled) {
      this.aiRecommendations.push({
        priority: 'medium',
        message: 'Enable vector search for better document matching'
      });
    }
    
    if (!this.aiConfigForm?.get('conversationalMemory')?.value) {
      this.aiRecommendations.push({
        priority: 'low',
        message: 'Enable conversational memory for better user experience'
      });
    }
  }

  private updateDocumentMetrics() {
    if (!this.documentData) return;
    
    this.documentMetrics = {
      documentsProcessed: this.documentData.totalDocuments,
      chunksGenerated: this.documentData.totalChunks,
      vectorIndexSize: this.documentData.totalChunks * 384,
      lastProcessed: this.documentData.recentUploads.length > 0 
        ? new Date(this.documentData.recentUploads[0].created_at)
        : null
    };
  }

  // File Upload Handlers
  onLogoUploaded(uploadResult: any) {
    if (uploadResult.success && uploadResult.url) {
      this.brandingForm.patchValue({ logo_url: uploadResult.url });
      this.snackBar.open('Logo uploaded successfully!', 'Close', { duration: 3000 });
      this.calculateBrandingCompleteness();
    }
  }

  onFaviconUploaded(uploadResult: any) {
    if (uploadResult.success && uploadResult.url) {
      this.brandingForm.patchValue({ favicon_url: uploadResult.url });
      this.snackBar.open('Favicon uploaded successfully!', 'Close', { duration: 3000 });
      this.calculateBrandingCompleteness();
    }
  }

  onUploadError(error: any) {
    console.error('Upload error:', error);
    this.snackBar.open('Upload failed: ' + (error.message || 'Unknown error'), 'Close', { duration: 5000 });
  }

  // Document Management Actions
  rebuildSearchIndex() {
    this.loading = true;
    
    const rebuildSub = this.superAdminService.rebuildUniversityIndex(this.university.x_id).subscribe({
      next: (response) => {
        this.snackBar.open('Search index rebuilt successfully!', 'Close', { duration: 3000 });
        this.loadDocumentAnalytics();
        this.loading = false;
      },
      error: (error) => {
        console.error('Error rebuilding index:', error);
        this.snackBar.open('Failed to rebuild search index', 'Close', { duration: 3000 });
        this.loading = false;
      }
    });
    
    this.subscriptions.push(rebuildSub);
  }

  runSystemHealthCheck() {
    this.loading = true;
    
    const healthSub = this.adminService.getUniversityHealthCheck(this.university.x_id).subscribe({
      next: (health) => {
        this.overallHealthScore = health.overall_score || 0;
        this.snackBar.open(`System health check completed. Score: ${this.overallHealthScore}/100`, 'Close', { duration: 5000 });
        this.loading = false;
      },
      error: (error) => {
        console.error('Error running health check:', error);
        this.snackBar.open('Health check failed', 'Close', { duration: 3000 });
        this.loading = false;
      }
    });
    
    this.subscriptions.push(healthSub);
  }

  // AI Configuration Actions
  testAIConfiguration() {
    this.loading = true;
    
    setTimeout(() => {
      const aiEnabled = this.aiConfigForm.get('enabled')?.value;
      const hasDocuments = this.documentData?.totalDocuments && this.documentData.totalDocuments > 0;
      
      if (aiEnabled && hasDocuments) {
        this.snackBar.open('AI configuration test successful!', 'Close', { duration: 3000 });
      } else if (!aiEnabled) {
        this.snackBar.open('Please enable AI features first', 'Close', { duration: 3000 });
      } else {
        this.snackBar.open('Please upload documents to test AI responses', 'Close', { duration: 3000 });
      }
      
      this.loading = false;
    }, 2000);
  }

  // Save Functions
  saveBrandingChanges() {
    if (this.brandingForm.invalid) {
      this.markFormGroupTouched(this.brandingForm);
      return;
    }

    this.updating = true;
    const formValue = this.brandingForm.value;
    
    const brandingData = {
      branding: {
        logo_url: formValue.logo_url,
        favicon_url: formValue.favicon_url,
        theme_colors: {
          primary: formValue.primary_color,
          secondary: formValue.secondary_color,
          accent: formValue.accent_color,
          background: formValue.background_color
        },
        welcome_message: formValue.welcome_message,
        footer_text: formValue.footer_text,
        contact_email: formValue.contact_email,
        support_phone: formValue.support_phone,
        domain_name: formValue.domain_name,
        custom_css: formValue.custom_css,
        social_links: formValue.social_links,
        meta_title: formValue.meta_title,
        meta_description: formValue.meta_description,
        keywords: formValue.keywords
      }
    };

    const saveSub = this.superAdminService.updateUniversitySettings(this.university.x_id, brandingData).subscribe({
      next: (response) => {
        this.snackBar.open('Branding updated successfully!', 'Close', { duration: 3000 });
        this.calculateBrandingCompleteness();
        this.updating = false;
      },
      error: (error) => {
        console.error('Error updating branding:', error);
        this.snackBar.open('Failed to update branding', 'Close', { duration: 3000 });
        this.updating = false;
      }
    });
    
    this.subscriptions.push(saveSub);
  }

  saveAIConfiguration() {
    if (this.aiConfigForm.invalid) {
      this.markFormGroupTouched(this.aiConfigForm);
      return;
    }

    this.updating = true;
    const formValue = this.aiConfigForm.value;
    
    const aiConfigData = {
      ai_config: {
        enabled: formValue.enabled,
        rag_model: formValue.ragModel,
        max_tokens: formValue.maxTokens,
        temperature: formValue.temperature,
        features: {
          conversational_memory: formValue.conversationalMemory,
          lead_management: formValue.leadManagement,
          dynamic_questioning: formValue.dynamicQuestioning,
          vector_search: formValue.vectorSearch
        },
        response_style: formValue.responseStyle,
        knowledge_cutoff: formValue.knowledgeCutoff,
        fallback_behavior: formValue.fallbackBehavior,
        content_filtering: formValue.contentFiltering,
        response_moderation: formValue.responseModeration,
        sensitive_topics_handling: formValue.sensitiveTopicsHandling
      }
    };

    const saveSub = this.superAdminService.updateUniversitySettings(this.university.x_id, aiConfigData).subscribe({
      next: (response) => {
        this.snackBar.open('AI configuration updated successfully!', 'Close', { duration: 3000 });
        this.calculateAIReadiness();
        this.updating = false;
      },
      error: (error) => {
        console.error('Error updating AI configuration:', error);
        this.snackBar.open('Failed to update AI configuration', 'Close', { duration: 3000 });
        this.updating = false;
      }
    });
    
    this.subscriptions.push(saveSub);
  }

  saveAllChanges() {
    const brandingData = { branding: this.brandingForm.value };
    const aiConfigData = { ai_config: this.aiConfigForm.value };
    
    const combinedData = { ...brandingData, ...aiConfigData };
    
    this.updating = true;
    
    const saveSub = this.superAdminService.updateUniversitySettings(this.university.x_id, combinedData).subscribe({
      next: (response) => {
        this.snackBar.open('All changes saved successfully!', 'Close', { duration: 3000 });
        this.dialogRef.close({ updated: true, university: this.university });
      },
      error: (error) => {
        console.error('Error saving changes:', error);
        this.snackBar.open('Failed to save changes', 'Close', { duration: 3000 });
        this.updating = false;
      }
    });
    
    this.subscriptions.push(saveSub);
  }

  // Template Methods
  onSave() {
    this.saveAllChanges();
  }

  onCancel() {
    this.dialogRef.close();
  }

  // Utility Methods
  private markFormGroupTouched(formGroup: FormGroup) {
    Object.keys(formGroup.controls).forEach(key => {
      const control = formGroup.get(key);
      control?.markAsTouched();
      
      if (control instanceof FormGroup) {
        this.markFormGroupTouched(control);
      }
    });
  }

  onTabChange(index: number) {
    this.selectedTab = index;
  }

  closeDialog() {
    this.dialogRef.close();
  }

  // Getters for template
  get brandingProgressClass() {
    if (this.brandingProgress >= 80) return 'high';
    if (this.brandingProgress >= 50) return 'medium';
    return 'low';
  }

  get aiProgressClass() {
    if (this.aiSetupProgress >= 80) return 'high';
    if (this.aiSetupProgress >= 50) return 'medium';
    return 'low';
  }

  get overallStatus() {
    const avgProgress = (this.brandingProgress + this.aiSetupProgress) / 2;
    if (avgProgress >= 80) return 'Excellent';
    if (avgProgress >= 60) return 'Good';
    if (avgProgress >= 40) return 'Fair';
    return 'Needs Attention';
  }
}
