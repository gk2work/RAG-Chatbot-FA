// file-upload.service.ts
import { Injectable } from "@angular/core";
import { HttpClient, HttpEventType, HttpRequest, HttpHeaders } from "@angular/common/http";
import { Observable, Subject } from "rxjs";
import { map } from "rxjs/operators";
import { environment } from "../../environments/environment";

export interface UploadProgress {
  progress: number;
  file: File;
  status: "uploading" | "completed" | "error";
  url?: string;
  error?: string;
}

export interface UploadResponse {
  success: boolean;
  url: string;
  filename: string;
  size: number;
  error?: string;
}

@Injectable({
  providedIn: "root",
})
export class FileUploadService {
  // ✅ FIXED: environment.apiUrl already includes /api, so don't add it again
  private apiUrl = `${environment.apiUrl}/upload`;

  // Observable for upload progress
  private uploadProgress$ = new Subject<UploadProgress>();

  constructor(private http: HttpClient) {}

  /**
   * Get authentication headers for upload requests
   */
  private getAuthHeaders(): HttpHeaders {
  const token = localStorage.getItem('authToken');
  const headers = new HttpHeaders();
  return token ? headers.set('Authorization', `Bearer ${token}`) : headers;
}

  /**
   * Upload a single file with progress tracking
   */
  uploadFile(file: File, folder: string = "logos"): Observable<UploadProgress> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("folder", folder);

    const endpoint =
      folder === "favicons" ? `${this.apiUrl}/favicon` : `${this.apiUrl}/logo`;
    const uploadRequest = new HttpRequest('POST', endpoint, formData, {
  reportProgress: true,
  headers: this.getAuthHeaders()
});

    return this.http.request<UploadResponse>(uploadRequest).pipe(
      map((event) => {
        switch (event.type) {
          case HttpEventType.UploadProgress:
            const progress = Math.round(
              (100 * event.loaded) / (event.total || 1)
            );
            return {
              progress,
              file,
              status: "uploading" as const,
            };

          case HttpEventType.Response:
            if (event.body?.success) {
              return {
                progress: 100,
                file,
                status: "completed" as const,
                url: event.body.url,
              };
            } else {
              return {
                progress: 0,
                file,
                status: "error" as const,
                error: event.body?.error || "Upload failed",
              };
            }

          default:
            return {
              progress: 0,
              file,
              status: "uploading" as const,
            };
        }
      })
    );
  }

  /**
   * Validate image file
   */
  validateImageFile(file: File): { valid: boolean; error?: string } {
    // Check file type
    const allowedTypes = [
      "image/png",
      "image/jpeg",
      "image/jpg",
      "image/svg+xml",
      "image/x-icon", 
      "image/vnd.microsoft.icon"
    ];
    if (!allowedTypes.includes(file.type)) {
      return {
        valid: false,
        error: "Only PNG, JPG, and SVG files are allowed",
      };
    }

    // Check file size (5MB max for logos)
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
      return { valid: false, error: "File size must be less than 5MB" };
    }

    return { valid: true };
  }

  /**
   * Get upload progress observable
   */
  getUploadProgress(): Observable<UploadProgress> {
    return this.uploadProgress$.asObservable();
  }
}
