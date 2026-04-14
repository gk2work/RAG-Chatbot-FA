// create-user-dialog.component.ts
import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { SuperAdminService } from '../../../services/super-admin.service';

export interface CreateUserData {
  name: string;
  email: string;
  password: string;
  role: string;
  university_id?: string;
  first_name: string;
  last_name: string;
}

@Component({
  selector: 'app-create-user-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSelectModule,
    MatSnackBarModule
  ],
  templateUrl: './create-user-dialog.component.html',
  styleUrls: ['./create-user-dialog.component.scss']
})
export class CreateUserDialogComponent implements OnInit {
  userForm: FormGroup;
  creating = false;
  
  roles = [
    { value: 'admin', label: 'Admin', description: 'University administrator' },
    { value: 'student', label: 'Student', description: 'Student user' }
  ];
  
 // Universities with proper typing
   universities: Array<{x_id: string, name: string, code: string}> = [];

  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<CreateUserDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any,
    private snackBar: MatSnackBar,
    private superAdminService: SuperAdminService
  ) {
    this.userForm = this.fb.group({
      first_name: ['', [Validators.required, Validators.minLength(2)]],
      last_name: ['', [Validators.required, Validators.minLength(2)]],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      role: ['admin', [Validators.required]],
      university_x_id: ['']
    });
  }

  ngOnInit() {
    // Load universities from API in next step
    this.loadUniversities();
    
    // Watch role changes to show/hide university selection
this.userForm.get('role')?.valueChanges.subscribe(role => {
  const universityControl = this.userForm.get('university_x_id');
  if (role === 'admin') {
    universityControl?.setValidators([Validators.required]);
  } else {
    universityControl?.clearValidators();
    universityControl?.setValue('');
  }
  universityControl?.updateValueAndValidity();
});
  }

loadUniversities() {
  this.superAdminService.getUniversities().subscribe({
    next: (response: any) => {
      if (response.success && response.universities) {
        this.universities = response.universities;
      }
    },
    error: (error: any) => {
      console.error('Error loading universities:', error);
      this.snackBar.open('Failed to load universities', 'Close', { duration: 3000 });
    }
  });
}

  onCancel(): void {
    this.dialogRef.close();
  }

  onCreate(): void {
  if (this.userForm.valid) {
    this.creating = true;
    
    // 🔍 DEBUG: Log all form values for troubleshooting
    console.log('🔍 DEBUG: All form values:', this.userForm.value);
    console.log('🔍 DEBUG: Role value:', this.userForm.value.role);
    console.log('🔍 DEBUG: University X-ID value:', this.userForm.value.university_x_id);
    console.log('🔍 DEBUG: Is admin role?', this.userForm.value.role === 'admin');
    console.log('🔍 DEBUG: Has university X-ID?', !!this.userForm.value.university_x_id);
    
    const formData: any = {
      email: this.userForm.value.email,
      password: this.userForm.value.password,
      role: this.userForm.value.role,
      first_name: this.userForm.value.first_name,
      last_name: this.userForm.value.last_name
    };

    // Add university_x_id for admin users  
    if (this.userForm.value.role === 'admin' && this.userForm.value.university_x_id) {
      formData.university_x_id = this.userForm.value.university_x_id;
      console.log('✅ DEBUG: Added university X-ID to form data:', formData.university_x_id);
    } else if (this.userForm.value.role === 'admin') {
      console.log('❌ DEBUG: Admin role selected but no university X-ID found!');
    }

    console.log('🚀 Creating user with final data:', formData);

    this.superAdminService.createAdminUser(formData).subscribe({
      next: (response: any) => {
        this.snackBar.open('User created successfully!', 'Close', { duration: 3000 });
        this.dialogRef.close(response);
      },
      error: (error: any) => {
        console.error('Error creating user:', error);
        this.snackBar.open('Failed to create user', 'Close', { duration: 3000 });
      }
    });
  }
}

  // Helper methods for template
  get isAdminRole(): boolean {
    return this.userForm.get('role')?.value === 'admin';
  }

  get emailError(): string {
    const emailControl = this.userForm.get('email');
    if (emailControl?.hasError('required')) return 'Email is required';
    if (emailControl?.hasError('email')) return 'Please enter a valid email';
    return '';
  }

  get passwordError(): string {
    const passwordControl = this.userForm.get('password');
    if (passwordControl?.hasError('required')) return 'Password is required';
    if (passwordControl?.hasError('minlength')) return 'Password must be at least 6 characters';
    return '';
  }
}