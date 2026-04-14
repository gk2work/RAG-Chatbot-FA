// pdf-upload.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, map, catchError, throwError } from 'rxjs';
import { environment } from '../../environments/environment';

export interface PdfUploadProgress {
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  message?: string;
  error?: string;
}

export interface PdfUploadResult {
  success: boolean;
  document_id?: string;
  file_id?: string;
  chunk_count?: number;
  vector_index_built?: boolean;
  pages_processed?: number;
  text_length?: number;
  error?: string;
}

@Injectable({
  providedIn: 'root'
})
export class PdfUploadService {
  private baseUrl = `${environment.apiUrl}`;

  constructor(private http: HttpClient) {}

  private getAuthHeaders(): HttpHeaders {
    const token = localStorage.getItem('authToken');
    return new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
  }

  private getAuthHeadersForFormData(): HttpHeaders {
    const token = localStorage.getItem('authToken');
    // Don't set Content-Type for FormData - let browser set it with boundary
    return new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
  }

  /**
   * Upload PDF file for a specific university using X-ID
   */
  uploadPdf(universityXId: string, file: File): Observable<PdfUploadProgress> {
    console.log('🔍 Upload Debug Info:');
    console.log('- University X-ID:', universityXId);
    console.log('- File name:', file.name);
    console.log('- File size:', file.size);
    console.log('- File type:', file.type);
    console.log('- Base URL:', this.baseUrl);
    console.log('- Full endpoint:', `${this.baseUrl}/university/${universityXId}/upload_pdf`);
    
    const token = localStorage.getItem('authToken');
    console.log('- Auth token exists:', !!token);
    console.log('- Auth token length:', token?.length || 0);

    const formData = new FormData();
    formData.append('file', file, file.name);
    formData.append('university_x_id', universityXId);

    return this.http.post(`${this.baseUrl}/university/${universityXId}/upload_pdf`, formData, {
      headers: this.getAuthHeadersForFormData(),
      reportProgress: true,
      observe: 'events'
    }).pipe(
      map((event: HttpEvent<any>) => {
        switch (event.type) {
          case HttpEventType.UploadProgress:
            if (event.total) {
              const progress = Math.round(100 * event.loaded / event.total);
              return {
                progress,
                status: 'uploading' as const,
                message: `Uploading... ${progress}%`
              };
            }
            return {
              progress: 0,
              status: 'uploading' as const,
              message: 'Starting upload...'
            };

          case HttpEventType.Response:
            const result = event.body as any;
            console.log('🎉 Upload response received:', result);
            
            // Check for successful response - backend returns different formats
            const isSuccess = result.success === true || 
                             (result.message && result.message.includes('successfully')) ||
                             (result.chunk_count !== undefined);
            
            if (isSuccess) {
              const chunkCount = result.chunk_count || result.processing_stats?.chunk_count || 0;
              const pagesProcessed = result.pages_processed || result.processing_stats?.pages_processed || 0;
              
              return {
                progress: 100,
                status: 'completed' as const,
                message: `✅ Upload successful! Processed ${pagesProcessed} pages, created ${chunkCount} text chunks. Document ready for AI search.`
              };
            } else {
              console.error('❌ Upload failed with response:', result);
              return {
                progress: 0,
                status: 'error' as const,
                error: result.error || result.message || 'Upload failed'
              };
            }

          default:
            return {
              progress: 50,
              status: 'processing' as const,
              message: 'Processing document...'
            };
        }
      }),
      catchError((error) => {
        let errorMessage = 'Upload failed';
        
        if (error.error?.error) {
          errorMessage = error.error.error;
        } else if (error.message) {
          errorMessage = error.message;
        }

        return throwError(() => ({
          progress: 0,
          status: 'error' as const,
          error: errorMessage
        }));
      })
    );
  }

  /**
   * Validate PDF file before upload
   */
  validatePdfFile(file: File): { valid: boolean; error?: string } {
    // Check file type
    if (file.type !== 'application/pdf') {
      return {
        valid: false,
        error: 'Only PDF files are allowed'
      };
    }

    // Check file size (50MB max for PDFs)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      return {
        valid: false,
        error: `File size must be less than ${maxSize / (1024 * 1024)}MB`
      };
    }

    // Check if file name is valid
    if (!file.name || file.name.trim().length === 0) {
      return {
        valid: false,
        error: 'File must have a valid name'
      };
    }

    return { valid: true };
  }

  /**
   * Get uploaded documents for a university
   */
  getUniversityDocuments(universityXId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/university/${universityXId}/documents`, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Delete a document
   */
  deleteDocument(universityXId: string, documentId: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/university/${universityXId}/documents/${documentId}`, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Search university documents
   */
  searchDocuments(universityXId: string, query: string, method: 'text' | 'vector' = 'vector'): Observable<any> {
    return this.http.post(`${this.baseUrl}/university/${universityXId}/search`, {
      query,
      method,
      top_k: 10
    }, {
      headers: this.getAuthHeaders()
    }).pipe(
      catchError(this.handleError)
    );
  }

  private handleError(error: any): Observable<never> {
    let errorMessage = 'An error occurred';
    
    if (error.error?.error) {
      errorMessage = error.error.error;
    } else if (error.message) {
      errorMessage = error.message;
    }

    console.error('PDF Upload Service Error:', error);
    return throwError(() => new Error(errorMessage));
  }
}