// super-admin-universities.component.ts
import { Component, OnInit } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatCardModule } from "@angular/material/card";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatTableModule } from "@angular/material/table";
import { MatProgressSpinnerModule } from "@angular/material/progress-spinner";
import { SuperAdminService } from "../../../services/super-admin.service";
import { MatSnackBar, MatSnackBarModule } from "@angular/material/snack-bar";
import { MatDialog } from "@angular/material/dialog";
import { CreateUniversityDialogComponent } from "./create-university-dialog.component";
import { UniversityBrandingDialogComponent } from "./university-branding-dialog.component";
import { AdminDocumentManagementComponent } from '../../admin-portal/document-management/admin-document-management.component';

export interface University {
  _id: string;
  name: string;
  code: string;
  x_id: string;
  description: string;
  status: string;
  document_count: number;
  created_at: string;
  stats?: {
    total_leads: number;
    total_sessions: number;
    active_sessions: number;
    admins: number;
  };

  // ADD THESE BRANDING PROPERTIES:
  branding?: {
    logo_url?: string;
    favicon_url?: string;
    primary_color?: string;
    secondary_color?: string;
    accent_color?: string;
    custom_css?: string;
    font_family?: string;
    theme_name?: string;
  };

  // WHITE-LABELING PROPERTIES:
  domains?: {
    primary_domain?: string;
    custom_domains?: string[];
    subdomain?: string;
  };

  // ADDITIONAL BRANDING:
  contact_info?: {
    website_url?: string;
    support_email?: string;
    phone?: string;
    address?: string;
  };
}

@Component({
  selector: "app-super-admin-universities",
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  templateUrl: "./super-admin-universities.component.html",
  styleUrls: ["./super-admin-universities.component.scss"],
})
export class SuperAdminUniversitiesComponent implements OnInit {
  loading = true;
  error = "";
  universities: University[] = [];

  displayedColumns: string[] = [
    "name",
    "code",
    "x_id",
    "branding",
    "status",
    "stats",
    "actions",
  ];

  constructor(
    private superAdminService: SuperAdminService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {}

  ngOnInit() {
    this.loadUniversities();
  }

  loadUniversities() {
    this.loading = true;
    this.error = "";

    this.superAdminService.getUniversities().subscribe({
      next: (response: any) => {
        if (response.success && response.universities) {
          this.universities = response.universities;
          this.loading = false;
          console.log("✅ Universities loaded:", response.universities);
        } else {
          this.error = "Invalid response format from server";
          this.loading = false;
        }
      },
      error: (error: Error) => {
        this.error = error.message;
        this.loading = false;
        console.error("❌ Failed to load universities:", error);

        this.snackBar.open(
          `Failed to load universities: ${error.message}`,
          "Close",
          { duration: 5000 }
        );
      },
    });
  }

  onCreateUniversity() {
    console.log("🔍 Create University button clicked!");

    // Remove aria-hidden from app-root before opening dialog
    const appRoot = document.querySelector("app-root");
    if (appRoot) {
      appRoot.removeAttribute("aria-hidden");
      console.log("🔧 Removed aria-hidden from app-root");
    }

    const dialogRef = this.dialog.open(CreateUniversityDialogComponent, {
      width: "600px",
      maxWidth: "90vw",
      disableClose: false,
      autoFocus: true,
      hasBackdrop: true,
    });

    console.log("🔍 Dialog opened:", dialogRef);

    dialogRef.afterClosed().subscribe((result) => {
      console.log("Dialog closed with result:", result);
      if (result && result.success && result.refresh) {
        console.log("✅ University created, refreshing list...");
        // Refresh the universities list
        this.loadUniversities();
      }
    });
  }
onManageUniversityDocuments(university: any) {
  console.log('🔍 DEBUGGING - Full university object:', university);
  console.log('🔍 DEBUGGING - University x_id:', university.x_id);
  console.log('🔍 DEBUGGING - University name:', university.name);
  console.log('🔍 DEBUGGING - University code:', university.code);
  
  const dialogRef = this.dialog.open(AdminDocumentManagementComponent, {
    width: '1000px',
    maxWidth: '95vw',
    height: '80vh',
    disableClose: false,
    data: { 
      university,
      adminMode: false,
      universityContext: {
        x_id: university.x_id,
        code: university.code,
        name: university.name
      }
    }
  });
}

  onEditUniversity(university: University) {
    console.log("Edit university:", university);
  }

  onViewDetails(university: University) {
    console.log("View details:", university);
  }

  onManageBranding(university: University) {
    console.log("🎨 Opening branding dialog for university:", university.name);

    const dialogRef = this.dialog.open(UniversityBrandingDialogComponent, {
      width: "800px",
      maxWidth: "95vw",
      height: "600px",
      maxHeight: "90vh",
      disableClose: false,
      autoFocus: false,
      hasBackdrop: true,
      data: { university: university },
    });

    dialogRef.afterClosed().subscribe((result) => {
      console.log("Branding dialog closed with result:", result);
      if (result && result.success && result.refresh) {
        console.log("✅ Branding updated, refreshing universities list...");
        this.loadUniversities();

        this.snackBar.open(
          `Branding for "${university.name}" updated successfully!`,
          "Close",
          { duration: 5000 }
        );
      }
    });
  }
}
