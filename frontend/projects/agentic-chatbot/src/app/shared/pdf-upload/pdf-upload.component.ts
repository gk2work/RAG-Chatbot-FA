// pdf-upload.component.ts
import { Component, Input, Output, EventEmitter, OnInit } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatProgressBarModule } from "@angular/material/progress-bar";
import { MatSnackBar, MatSnackBarModule } from "@angular/material/snack-bar";
import { MatCardModule } from "@angular/material/card";
import { MatChipsModule } from "@angular/material/chips";
import { MatTooltipModule } from "@angular/material/tooltip";
import {
  PdfUploadService,
  PdfUploadProgress,
} from "../../services/pdf-upload.service";

export interface UploadedDocument {
  id: string;
  filename: string;
  pages: number;
  chunks: number;
  uploadDate: Date;
  size: number;
  // Enhanced properties
  searchType?: string;
  processingMethod?: string;
  hasVectorSearch?: boolean;
  contentPreview?: string;
  fileType?: string;
}

export interface ProcessingStage {
  name: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  message: string;
  icon: string;
}

@Component({
  selector: "app-pdf-upload",
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatProgressBarModule,
    MatSnackBarModule,
    MatCardModule,
    MatChipsModule,
    MatTooltipModule,
  ],
  templateUrl: "./pdf-upload.component.html",
  styleUrls: ["./pdf-upload.component.scss"],
})
export class PdfUploadComponent implements OnInit {
  @Input() universityXId: string = "";
  @Input() universityName: string = "";
  @Input() placeholder: string =
    "Drag and drop PDF documents here or click to browse";
  @Input() allowMultiple: boolean = true;
  @Input() showDocumentList: boolean = true;

  @Output() documentUploaded = new EventEmitter<any>();
  @Output() uploadProgress = new EventEmitter<number>();
  @Output() uploadError = new EventEmitter<string>();

  isDragOver = false;
  uploadQueue: Array<{
    file: File;
    progress: PdfUploadProgress;
    id: string;
    processingStages: ProcessingStage[];
  }> = [];

  uploadedDocuments: UploadedDocument[] = [];
  loading = false;

  constructor(
    private pdfUploadService: PdfUploadService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    if (this.universityXId && this.showDocumentList) {
      this.loadExistingDocuments();
    }
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFiles(Array.from(files));
    }
  }

  onFileSelected(event: any) {
    const files = event.target.files;
    if (files && files.length > 0) {
      this.handleFiles(Array.from(files));
    }
    // Reset input to allow selecting the same file again
    event.target.value = "";
  }

  
  handleFiles(files: File[]) {
    // ✅ STRICT X-ID VALIDATION
    if (!this.universityXId || this.universityXId.trim().length === 0) {
      this.snackBar.open(
        "ERROR: University X-ID is missing. Cannot upload documents.",
        "Close",
        {
          duration: 10000,
          panelClass: ["error-snackbar"],
        }
      );
      return;
    }

    // ✅ ENSURE UPPERCASE
    this.universityXId = this.universityXId.toUpperCase();

    console.log(`🏛️ Uploading to university X-ID: ${this.universityXId}`);

    // ✅ FIXED: Actually process the files
    const pdfFiles = files.filter(file => {
      if (file.type !== 'application/pdf') {
        this.snackBar.open(
          `File "${file.name}" is not a PDF. Only PDF files are supported.`,
          "Close",
          { duration: 5000, panelClass: ["error-snackbar"] }
        );
        return false;
      }
      return true;
    });

    if (pdfFiles.length === 0) {
      this.snackBar.open(
        "No valid PDF files found. Please select PDF files only.",
        "Close",
        { duration: 5000, panelClass: ["error-snackbar"] }
      );
      return;
    }

    // Process each valid PDF file
    pdfFiles.forEach(file => {
      this.processFile(file);
    });

    this.snackBar.open(
      `Starting upload of ${pdfFiles.length} PDF file(s) to ${this.universityName || this.universityXId}`,
      "Close",
      { duration: 3000, panelClass: ["success-snackbar"] }
    );
  }

  processFile(file: File) {
    // Validate file
    const validation = this.pdfUploadService.validatePdfFile(file);
    if (!validation.valid) {
      this.uploadError.emit(validation.error!);
      this.snackBar.open(validation.error!, "Close", { duration: 5000 });
      return;
    }

    // Add to upload queue with processing stages
    const uploadItem = {
      file,
      progress: {
        progress: 0,
        status: "uploading" as const,
        message: "Preparing upload...",
      },
      id: this.generateId(),
      processingStages: this.createProcessingStages()
    };

    this.uploadQueue.push(uploadItem);
    this.startUpload(uploadItem);
  }

  createProcessingStages(): ProcessingStage[] {
    return [
      {
        name: 'Upload',
        status: 'active',
        message: 'Uploading PDF file to server...',
        icon: 'cloud_upload'
      },
      {
        name: 'Extract',
        status: 'pending',
        message: 'Extracting text from PDF pages...',
        icon: 'text_fields'
      },
      {
        name: 'Process',
        status: 'pending',
        message: 'Creating searchable text chunks...',
        icon: 'auto_fix_high'
      },
      {
        name: 'Index',
        status: 'pending',
        message: 'Building AI search embeddings...',
        icon: 'psychology'
      },
      {
        name: 'Complete',
        status: 'pending',
        message: 'Document ready for intelligent search!',
        icon: 'check_circle'
      }
    ];
  }

  startUpload(uploadItem: any) {
    this.pdfUploadService
      .uploadPdf(this.universityXId, uploadItem.file)
      .subscribe({
        next: (progress: PdfUploadProgress) => {
          uploadItem.progress = progress;
          this.uploadProgress.emit(progress.progress);
          
          // Update processing stages based on progress
          this.updateProcessingStages(uploadItem, progress);

          if (progress.status === "completed") {
            this.onUploadComplete(uploadItem);
          } else if (progress.status === "error") {
            this.onUploadError(uploadItem, progress.error || "Upload failed");
          }
        },
        error: (error) => {
          console.error('🔥 Upload error details:', error);
          console.error('🔥 Error status:', error.status);
          console.error('🔥 Error message:', error.message);
          console.error('🔥 Error body:', error.error);
          
          let errorMessage = "Upload failed";
          if (error.error?.error) {
            errorMessage = error.error.error;
          } else if (error.message) {
            errorMessage = error.message;
          } else if (error.status) {
            errorMessage = `Upload failed with status ${error.status}`;
          }
          
          this.onUploadError(uploadItem, errorMessage);
        },
      });
  }

  updateProcessingStages(uploadItem: any, progress: PdfUploadProgress) {
    const stages = uploadItem.processingStages;
    
    // Reset all stages to pending first
    stages.forEach((stage: ProcessingStage) => {
      if (stage.status === 'active') stage.status = 'pending';
    });
    
    if (progress.status === 'uploading') {
      if (progress.progress < 100) {
        stages[0].status = 'active';
        stages[0].message = `Uploading PDF file... ${progress.progress}%`;
      } else {
        stages[0].status = 'completed';
        stages[1].status = 'active';
        stages[1].message = 'Server received file, extracting text...';
      }
    } else if (progress.status === 'processing') {
      stages[0].status = 'completed';
      stages[1].status = 'completed';
      stages[2].status = 'active';
      stages[2].message = 'Processing text into searchable chunks...';
    } else if (progress.status === 'completed') {
      stages.forEach((stage: ProcessingStage) => stage.status = 'completed');
      stages[4].message = progress.message || 'Document ready for AI-powered search!';
    } else if (progress.status === 'error') {
      const activeStageIndex = stages.findIndex((s: ProcessingStage) => s.status === 'active');
      if (activeStageIndex >= 0) {
        stages[activeStageIndex].status = 'error';
        stages[activeStageIndex].message = progress.error || 'Processing failed';
      }
    }
  }

  onUploadComplete(uploadItem: any) {
    this.snackBar.open(
      `✅ ${uploadItem.file.name} uploaded successfully!`,
      "Close",
      { duration: 3000 }
    );

    // Emit success event
    this.documentUploaded.emit({
      filename: uploadItem.file.name,
      universityXId: this.universityXId,
      progress: uploadItem.progress,
    });

    // Remove from queue after delay
    setTimeout(() => {
      this.removeFromQueue(uploadItem.id);
    }, 2000);

    // Reload document list
    if (this.showDocumentList) {
      this.loadExistingDocuments();
    }
  }

  onUploadError(uploadItem: any, error: string) {
    this.uploadError.emit(error);
    this.snackBar.open(
      `❌ Failed to upload ${uploadItem.file.name}: ${error}`,
      "Close",
      { duration: 5000 }
    );

    // Remove from queue after delay
    setTimeout(() => {
      this.removeFromQueue(uploadItem.id);
    }, 3000);
  }

  removeFromQueue(id: string) {
    this.uploadQueue = this.uploadQueue.filter((item) => item.id !== id);
  }

  triggerFileInput() {
    const fileInput = document.getElementById(
      "pdf-file-input"
    ) as HTMLInputElement;
    fileInput?.click();
  }

  loadExistingDocuments() {
    if (!this.universityXId) return;

    this.loading = true;
    this.pdfUploadService.getUniversityDocuments(this.universityXId).subscribe({
      next: (response) => {
        console.log('📄 Documents response received:', response);
        
        // Backend returns { documents: [...], summary: {...} }
        const documents = response.documents || [];
        
        // Transform backend documents to frontend format
        this.uploadedDocuments = documents.map((doc: any) => ({
          id: doc._id,
          filename: doc.title || 'Unknown Document',
          pages: doc.metadata?.pages_count || doc.enhanced_capabilities?.pages_processed || 1,
          chunks: doc.enhanced_capabilities?.chunk_count || 1,
          uploadDate: new Date(doc.created_at || Date.now()),
          size: doc.file_info?.size_bytes || doc.content_length || 0,
          // Additional info for display
          searchType: doc.search_type || 'text',
          processingMethod: doc.processing_method || 'legacy',
          hasVectorSearch: doc.enhanced_capabilities?.has_vector_search || false,
          contentPreview: doc.content_preview || '',
          fileType: doc.file_info?.type || doc.document_type || 'text'
        }));
        
        console.log('✅ Transformed documents:', this.uploadedDocuments);
        this.loading = false;
      },
      error: (error) => {
        console.error("❌ Error loading documents:", error);
        this.loading = false;
        this.snackBar.open(
          `Failed to load documents: ${error.message || 'Unknown error'}`,
          "Close",
          { duration: 5000, panelClass: ["error-snackbar"] }
        );
      },
    });
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  private generateId(): string {
    return Math.random().toString(36).substr(2, 9);
  }

  // Document management methods
  deleteDocument(doc: UploadedDocument) {
    if (confirm(`Are you sure you want to delete "${doc.filename}"?`)) {
      this.pdfUploadService
        .deleteDocument(this.universityXId, doc.id)
        .subscribe({
          next: () => {
            this.snackBar.open(
              `Document "${doc.filename}" deleted successfully`,
              "Close",
              { duration: 3000 }
            );
            this.loadExistingDocuments();
          },
          error: (error) => {
            this.snackBar.open(
              `Failed to delete document: ${error.message}`,
              "Close",
              { duration: 5000 }
            );
          },
        });
    }
  }

  searchDocuments(query: string) {
    if (!query.trim()) return;

    this.pdfUploadService.searchDocuments(this.universityXId, query).subscribe({
      next: (results) => {
        console.log("Search results:", results);
        // Handle search results - you might want to emit this or show in a dialog
      },
      error: (error) => {
        this.snackBar.open(`Search failed: ${error.message}`, "Close", {
          duration: 5000,
        });
      },
    });
  }
}
