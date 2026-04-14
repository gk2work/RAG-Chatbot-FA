// create-university-dialog.component.ts - REDESIGNED
import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { SuperAdminService } from '../../../services/super-admin.service';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { trigger, transition, style, animate } from '@angular/animations';

@Component({
  selector: 'app-create-university-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSnackBarModule
  ],
  templateUrl: './create-university-dialog.component.html',
  styleUrls: ['./create-university-dialog.component.scss'],
  animations: [
    trigger('slideInOut', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(-20px)' }),
        animate('300ms ease-in', style({ opacity: 1, transform: 'translateY(0)' }))
      ]),
      transition(':leave', [
        animate('300ms ease-out', style({ opacity: 0, transform: 'translateY(-20px)' }))
      ])
    ])
  ]
})
export class CreateUniversityDialogComponent implements OnInit {
  universityForm: FormGroup;
  creating = false;
  universityXId: string = '';

  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<CreateUniversityDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any,
    private superAdminService: SuperAdminService,
    private snackBar: MatSnackBar
  ) {
    this.universityForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(2)]],
      code: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(10)]],
      description: ['']
    });
  }

  ngOnInit() {
    // No additional initialization needed
  }



  onCancel(): void {
    this.dialogRef.close();
  }

onCreate(): void {
    if (this.universityForm.valid) {
      this.creating = true;
      
      const formData = {
        name: this.universityForm.value.name,
        code: this.universityForm.value.code.toUpperCase(),
        description: this.universityForm.value.description || ''
      };

      console.log('🚀 Creating university:', formData);

      this.superAdminService.createUniversity(formData).subscribe({
        next: (response) => {
          console.log('✅ University created successfully:', response);
          
          this.universityXId = response.x_id;
          this.creating = false;
          
          this.snackBar.open(
            `🎉 University "${formData.name}" created successfully!`,
            'Close',
            { duration: 4000, panelClass: ['success-snackbar'] }
          );

          // Show success state for 2 seconds, then close
          setTimeout(() => {
            this.dialogRef.close({ 
              success: true, 
              university: response,
              refresh: true 
            });
          }, 2000);
        },
        error: (error) => {
          console.error('❌ Failed to create university:', error);
          this.creating = false;
          
          this.snackBar.open(
            `❌ Failed to create university: ${error.message || 'Unknown error'}`,
            'Close',
            { duration: 6000, panelClass: ['error-snackbar'] }
          );
        }
      });
    }
  }

  onCodeInput(event: any): void {
    // Auto-convert to uppercase as user types
    const value = event.target.value.toUpperCase();
    this.universityForm.patchValue({ code: value });
  }

// Utility getters
  get isUniversityCreated(): boolean {
    return !!this.universityXId;
  }

  get universityName(): string {
    return this.universityForm.value.name || 'University';
  }
}