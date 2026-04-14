// FIXED super-admin-login.component.ts - Clean version without errors

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { trigger, state, style, transition, animate } from '@angular/animations';

// Material Design imports
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { environment } from 'projects/agentic-chatbot/src/environments/environment';

@Component({
  selector: 'app-unified-login',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatCheckboxModule
  ],
  templateUrl: './unified-login.component.html',
  styleUrls: ['./unified-login.component.scss'],
  animations: [
    trigger('slideIn', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(-20px)' }),
        animate('300ms ease-out', style({ opacity: 1, transform: 'translateY(0)' }))
      ])
    ])
  ]
})
export class UnifiedLoginComponent implements OnInit {
  loginForm: FormGroup;
  isLoading = false;
  hidePassword = true;
  errorMessage = '';

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private http: HttpClient,
    private snackBar: MatSnackBar
  ) {
    // Initialize form in constructor
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      rememberMe: [false]
    });
  }

  ngOnInit() {
    
    console.log('SuperAdmin Login Component initialized');
    console.log('Form created:', this.loginForm);
    this.checkExistingAuth();
  }

  private checkExistingAuth() {
  const token = localStorage.getItem('authToken');
  if (token) {
    console.log('User already logged in, checking current route');
    
    // Only redirect if we're actually on the login page
    const currentRoute = this.router.url;
    if (currentRoute === '/auth/login' || currentRoute === '/superadmin/login') {
      console.log('On login page with valid token, redirecting to dashboard');
      
      // Get user data to determine redirect
      const userData = localStorage.getItem('currentUser');
      if (userData) {
        const user = JSON.parse(userData);
        if (user.role === 'superadmin') {
          this.router.navigate(['/superadmin/dashboard']);
        } else if (user.role === 'admin') {
          this.router.navigate(['/admin/dashboard']);
        }
      }
    } else {
      console.log('Already on protected route, no redirect needed');
    }
  }
}

  togglePasswordVisibility() {
    this.hidePassword = !this.hidePassword;
    console.log('Password visibility toggled:', !this.hidePassword);
  }

onSubmit() {
  console.log('Form submitted!');
  console.log('Form valid:', this.loginForm.valid);
  
  if (this.loginForm.invalid) {
    console.log('Form is invalid');
    this.markFormGroupTouched();
    return;
  }

  // Clear any previous error messages
  this.errorMessage = '';
  this.isLoading = true;
  
  // Get form values
  const credentials = {
    email: this.loginForm.value.email,
    password: this.loginForm.value.password
  };
  
  console.log('🔐 Attempting login with:', { email: credentials.email });
  
  // Make real API call to backend
  // ✅ FIXED: environment.apiUrl already includes /api, so don't add it again
  const loginUrl = `${environment.apiUrl}/auth/login`;
  
  this.http.post<any>(loginUrl, credentials).subscribe({
    next: (response) => {
      console.log('✅ Login response:', response);
      
      // ✅ ADD THESE DEBUG LINES HERE
      console.log('🚨 RAW HTTP RESPONSE:', response);
      console.log('🚨 RAW USER OBJECT:', response.user);
      console.log('🚨 RAW USER PROPERTIES:', Object.keys(response.user || {}));
      console.log('🚨 RAW university_x_id:', response.user?.university_x_id);
      console.log('🚨 RAW university_code:', response.user?.university_code);
      
      this.handleLoginSuccess(response);
    },
    error: (error) => {
      console.error('❌ Login error:', error);
      this.handleLoginError(error);
    }
  });
}

// ADD these new methods to handle success and error responses:

private handleLoginSuccess(response: any) {
  this.isLoading = false;
  
  console.log('🎉 Login successful - Full response:', response);
  console.log('🏛️ User data:', response.user);
  
  // ✅ ADD THESE DEBUG LINES
  console.log('🔍 All user properties:', Object.keys(response.user));
  console.log('🔍 Direct access test:');
  console.log('  - university_x_id:', response.user.university_x_id);
  console.log('  - university_code:', response.user.university_code);
  console.log('  - universityXId:', response.user.universityXId);
  console.log('  - universityCode:', response.user.universityCode);
  
  if (response.token && response.user) {
    console.log('🎉 Login successful!');
    console.log('User role:', response.user.role);
    console.log('User data:', response.user);
    
    // Store JWT token and user data
    localStorage.setItem('authToken', response.token);
    localStorage.setItem('currentUser', JSON.stringify(response.user));
    
    const userRole = response.user.role;
    let redirectPath = '';
    
    if (userRole === 'superadmin') {
      redirectPath = '/superadmin/dashboard';
      this.snackBar.open('Welcome SuperAdmin! Redirecting...', 'Close', { 
        duration: 2000,
        panelClass: ['success-snackbar']
      });
    } else if (userRole === 'admin') {
      // ✅ IMPROVED: Try multiple property access patterns
      const universityXId = response.user.university_x_id || response.user.universityXId || response.user['university_x_id'];
      const universityCode = response.user.university_code || response.user.universityCode || response.user['university_code'];
      
      console.log('🏛️ Final extracted values:', { universityXId, universityCode });
      console.log('🏛️ Admin university assignment:', { universityXId, universityCode });
      
      if (universityXId && universityCode) {
        const universityContext = {
          x_id: universityXId,
          code: universityCode
        };
        
        localStorage.setItem('adminUniversityContext', JSON.stringify(universityContext));
        console.log('✅ University context stored successfully:', universityContext);
        
        redirectPath = '/admin/dashboard';
        this.snackBar.open(`Welcome ${universityCode.toUpperCase()} Admin! Redirecting...`, 'Close', { 
          duration: 2000,
          panelClass: ['success-snackbar']
        });
      } else {
        console.error('❌ Missing university assignment in user data');
        console.error('❌ Available user properties:', Object.keys(response.user));
        console.error('❌ Full user object:', response.user);
        this.errorMessage = 'Admin account not assigned to any university. Contact SuperAdmin.';
        this.snackBar.open('Admin account not assigned to university', 'Close', { 
          duration: 5000,
          panelClass: ['error-snackbar']
        });
        return;
      }
    } else {
      this.errorMessage = `Access denied. Role '${userRole}' is not authorized for this portal.`;
      this.snackBar.open('Access denied. Invalid role for admin portal.', 'Close', { 
        duration: 5000,
        panelClass: ['error-snackbar']
      });
      return;
    }
    
    // Perform redirect
    console.log(`🚀 Redirecting ${userRole} to:`, redirectPath);
    setTimeout(() => {
      this.router.navigateByUrl(redirectPath)
        .then(success => {
          console.log('✅ Navigation success:', success);
          // ✅ VERIFY STORAGE AFTER REDIRECT
          console.log('🔍 Stored currentUser:', localStorage.getItem('currentUser'));
          console.log('🔍 Stored adminUniversityContext:', localStorage.getItem('adminUniversityContext'));
        })
        .catch(error => console.log('❌ Navigation error:', error));
    }, 1000);
    
  } else {
    this.errorMessage = 'Invalid response from server. Please try again.';
    this.snackBar.open('Invalid response from server', 'Close', { duration: 5000 });
  }
}

private handleLoginError(error: any) {
  this.isLoading = false;
  
  console.error('Login error details:', error);
  
  let errorMessage = 'Login failed. Please try again.';
  
  if (error.status === 0) {
    // Network error
    errorMessage = 'Cannot connect to server. Please check your connection.';
  } else if (error.status === 401) {
    // Unauthorized
    errorMessage = 'Invalid email or password.';
  } else if (error.status === 403) {
    // Forbidden
    errorMessage = 'Access denied. SuperAdmin privileges required.';
  } else if (error.status >= 500) {
    // Server error
    errorMessage = 'Server error. Please try again later.';
  } else if (error.error?.error) {
    // Custom error message from backend
    errorMessage = error.error.error;
  } else if (error.error?.message) {
    // Alternative error message format
    errorMessage = error.error.message;
  }
  
  // Set error message for display
  this.errorMessage = errorMessage;
  
  // Show error snackbar
  this.snackBar.open(errorMessage, 'Close', { 
    duration: 5000,
    panelClass: ['error-snackbar']
  });
  
  // Clear password field on error (security best practice)
  this.loginForm.patchValue({ password: '' });
}

  private markFormGroupTouched() {
    Object.keys(this.loginForm.controls).forEach(key => {
      const control = this.loginForm.get(key);
      if (control) {
        control.markAsTouched();
        console.log(`Field ${key} marked as touched`);
      }
    });
  }
  logout() {
  // Clear all stored data
  localStorage.removeItem('authToken');
  localStorage.removeItem('currentUser');
  localStorage.removeItem('adminUniversityContext');
  
  // Navigate to login page
  this.router.navigate(['/auth/login']);
  
  // Show success message
  this.snackBar.open('Logged out successfully', 'Close', { 
    duration: 2000 
  });
}


}