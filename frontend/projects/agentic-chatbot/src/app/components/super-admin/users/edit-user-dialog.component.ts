// edit-user-dialog.component.ts
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

export interface EditUserData {
  user: any; // The user being edited
}

@Component({
  selector: 'app-edit-user-dialog',
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
  templateUrl: './edit-user-dialog.component.html',
  styleUrls: ['./edit-user-dialog.component.scss']
})
export class EditUserDialogComponent implements OnInit {
  userForm: FormGroup;
  updating = false;

  roles = [
    { value: 'admin', label: 'Admin', description: 'University administrator' },
    { value: 'student', label: 'Student', description: 'Student user' }
  ];

  universities: Array<{x_id: string, name: string, code: string}> = [];

  get isAdminRole(): boolean {
    return this.userForm.get('role')?.value === 'admin';
  }
  
  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<EditUserDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: EditUserData,
    private snackBar: MatSnackBar,
    private superAdminService: SuperAdminService
  ) {
    // Initialize form with user data
  const user = this.data.user;
  
  this.userForm = this.fb.group({
    first_name: [user.profile?.first_name || '', [Validators.required, Validators.minLength(2)]],
    last_name: [user.profile?.last_name || '', [Validators.required, Validators.minLength(2)]],
    email: [user.email, [Validators.required, Validators.email]],
    role: [user.role, [Validators.required]],
    university_x_id: [user.university_x_id || ''],
    is_active: [user.is_active]
  });
  }

  ngOnInit() {
    console.log('🔧 Editing user:', this.data.user);
  
  // Load universities for role/university assignment
  this.loadUniversities();
  
  // Set up role validation (admin users need university)
  this.setupRoleValidation();
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
    }
  });
}

setupRoleValidation() {
  const universityControl = this.userForm.get('university_id');
  
  this.userForm.get('role')?.valueChanges.subscribe(role => {
    if (role === 'admin') {
      universityControl?.setValidators([Validators.required]);
    } else {
      universityControl?.clearValidators();
    }
    universityControl?.updateValueAndValidity();
  });
}

onCancel() {
  this.dialogRef.close();
}

onUpdate() {
  if (this.userForm.valid) {
    this.updating = true;
    
    const updateData = {
      user_id: this.data.user._id,
      ...this.userForm.value
    };
    
    console.log('📝 Updating user with data:', updateData);
    
    // Try real API first, fallback to simulation if backend not ready
    this.superAdminService.updateUser(this.data.user._id, updateData).subscribe({
      next: (response: any) => {
        this.updating = false;
        console.log('✅ User update response:', response);
        
        this.snackBar.open('User updated successfully!', 'Close', { duration: 3000 });
        this.dialogRef.close({ success: true, user: response.user });
      },
      error: (error: any) => {
        console.error('Error updating user:', error);
        this.snackBar.open('Failed to update user', 'Close', { duration: 3000 });
      }
    });
  } else {
    this.snackBar.open('Please fix form errors before updating', 'Close', { duration: 3000 });
  }
}
}

