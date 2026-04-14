// file-upload.component.ts
import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { FileUploadService, UploadProgress } from '../../services/file-upload.service';

@Component({
  selector: 'app-file-upload',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatProgressBarModule,
    MatSnackBarModule
  ],
  templateUrl: './file-upload.component.html',
  styleUrls: ['./file-upload.component.scss']
})
export class FileUploadComponent implements OnInit {
  @Input() acceptedTypes: string = 'image/*';
  @Input() maxFileSize: number = 5 * 1024 * 1024; // 5MB default
  @Input() uploadFolder: string = 'logos';
  @Input() previewUrl: string = '';
  @Input() placeholder: string = 'Drag and drop your logo here or click to browse';
  
  @Output() fileUploaded = new EventEmitter<string>(); // Emits uploaded file URL
  @Output() uploadError = new EventEmitter<string>();
  @Output() uploadProgress = new EventEmitter<number>();

  isDragOver = false;
  isUploading = false;
  uploadProgressValue = 0;
  previewImageUrl: string = '';

  constructor(
    private fileUploadService: FileUploadService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.previewImageUrl = this.previewUrl;
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
      this.handleFile(files[0]);
    }
  }

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.handleFile(file);
    }
  }

  handleFile(file: File) {
    // Validate file
    const validation = this.fileUploadService.validateImageFile(file);
    if (!validation.valid) {
      this.uploadError.emit(validation.error!);
      this.snackBar.open(validation.error!, 'Close', { duration: 5000 });
      return;
    }

    // Create preview
    this.createPreview(file);

    // Start upload
    this.startUpload(file);
  }

  createPreview(file: File) {
    const reader = new FileReader();
    reader.onload = (e) => {
      this.previewImageUrl = e.target?.result as string;
    };
    reader.readAsDataURL(file);
  }

  startUpload(file: File) {
    this.isUploading = true;
    this.uploadProgressValue = 0;

    this.fileUploadService.uploadFile(file, this.uploadFolder).subscribe({
      next: (progress: UploadProgress) => {
        this.uploadProgressValue = progress.progress;
        this.uploadProgress.emit(progress.progress);

        if (progress.status === 'completed' && progress.url) {
          this.isUploading = false;
          this.fileUploaded.emit(progress.url);
          this.snackBar.open('File uploaded successfully!', 'Close', { duration: 3000 });
        } else if (progress.status === 'error') {
          this.isUploading = false;
          const errorMsg = progress.error || 'Upload failed';
          this.uploadError.emit(errorMsg);
          this.snackBar.open(errorMsg, 'Close', { duration: 5000 });
        }
      },
      error: (error) => {
        this.isUploading = false;
        const errorMsg = 'Upload failed. Please try again.';
        this.uploadError.emit(errorMsg);
        this.snackBar.open(errorMsg, 'Close', { duration: 5000 });
        console.error('Upload error:', error);
      }
    });
  }

  triggerFileInput() {
    const fileInput = document.getElementById('file-input') as HTMLInputElement;
    fileInput?.click();
  }

  removeImage() {
    this.previewImageUrl = '';
    this.fileUploaded.emit(''); // Emit empty URL to clear
  }
}