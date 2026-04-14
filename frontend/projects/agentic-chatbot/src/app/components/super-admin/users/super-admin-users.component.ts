// super-admin-users.component.ts
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatChipsModule } from '@angular/material/chips';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { SuperAdminService } from '../../../services/super-admin.service';
import { MatDialog } from '@angular/material/dialog';
import { CreateUserDialogComponent } from './create-user-dialog.component';
import { EditUserDialogComponent } from './edit-user-dialog.component';




export interface User {
  _id: string;
  email: string;
  role: string;
  created_at: string;
  created_by?: string;
  is_active: boolean;
  last_login?: string;
  university_id?: string;
  university_name?: string;
  university_code?: string;
  university_x_id?: string;
  profile?: {
    first_name: string;
    last_name: string;
    phone: string;
  };
}

@Component({
  selector: 'app-super-admin-users',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
    MatChipsModule,
    MatSelectModule,
    MatFormFieldModule
  ],
  templateUrl: './super-admin-users.component.html',
  styleUrls: ['./super-admin-users.component.scss']
})
export class SuperAdminUsersComponent implements OnInit {
  loading = true;
  error = '';
  users: User[] = [];
  filteredUsers: User[] = [];
  
  displayedColumns: string[] = ['user', 'role', 'university', 'status', 'lastLogin', 'actions'];
  
  // Filter options
  selectedRoleFilter = 'all';
  selectedStatusFilter = 'all';
  roleFilters = [
    { value: 'all', label: 'All Roles' },
    { value: 'superadmin', label: 'SuperAdmins' },
    { value: 'admin', label: 'Admins' },
    { value: 'student', label: 'Students' }
  ];
  
  statusFilters = [
    { value: 'all', label: 'All Status' },
    { value: 'active', label: 'Active Only' },
    { value: 'inactive', label: 'Inactive Only' }
  ];

  constructor(
    private snackBar: MatSnackBar,
    private superAdminService: SuperAdminService,
    private dialog: MatDialog
  ) {}

  ngOnInit() {
    this.loadUsers();
  }

loadUsers() {
  this.loading = true;
  this.error = '';

  // Build filters object
  const filters: any = {
    limit: 50  // Get up to 50 users
  };

  console.log('🚀 Loading users with filters:', filters);

  this.superAdminService.getUsers(filters).subscribe({
    next: (response: any) => {
      if (response.success && response.users) {
        this.users = response.users;
        this.applyFilters(); // Apply current filters to new data
        this.loading = false;
        console.log('✅ Users loaded:', response.users);
      } else {
        this.error = 'Invalid response format from server';
        this.loading = false;
      }
    },
    error: (error: Error) => {
      this.error = error.message;
      this.loading = false;
      console.error('❌ Failed to load users:', error);
      
      this.snackBar.open(
        `Failed to load users: ${error.message}`, 
        'Close', 
        { duration: 5000 }
      );
    }
  });
}

  applyFilters() {
    this.filteredUsers = this.users.filter(user => {
      const roleMatch = this.selectedRoleFilter === 'all' || user.role === this.selectedRoleFilter;
      const statusMatch = this.selectedStatusFilter === 'all' || 
                         (this.selectedStatusFilter === 'active' && user.is_active) ||
                         (this.selectedStatusFilter === 'inactive' && !user.is_active);
      
      return roleMatch && statusMatch;
    });
  }

  onRoleFilterChange() {
    this.applyFilters();
  }

  onStatusFilterChange() {
    this.applyFilters();
  }

 onCreateUser() {
  console.log('🔍 Create User button clicked!');
  
  const dialogRef = this.dialog.open(CreateUserDialogComponent, {
    width: '700px',
    maxWidth: '90vw',
    disableClose: false,
    autoFocus: false,
    hasBackdrop: true,
    panelClass: 'create-user-dialog'
  });

  console.log('🔍 Dialog opened:', dialogRef);

  dialogRef.afterClosed().subscribe(result => {
    console.log('Dialog closed with result:', result);
    if (result && result.success && result.refresh) {
      console.log('✅ User created, refreshing list...');
      // Refresh the users list
      this.loadUsers();
      
      // Show success message
      this.snackBar.open(
        `User "${result.user.name}" created successfully!`, 
        'Close', 
        { duration: 5000 }
      );
    }
  });
}

onEditUser(user: User) {
  console.log('🔧 Opening edit dialog for user:', user);
  
  const dialogRef = this.dialog.open(EditUserDialogComponent, {
    width: '600px',
    maxWidth: '90vw',
    disableClose: false,
    autoFocus: false,
    hasBackdrop: true,
    data: { user: user }
  });

  dialogRef.afterClosed().subscribe(result => {
    console.log('Edit dialog closed with result:', result);
    if (result && result.success && result.refresh) {
      console.log('✅ User updated, refreshing list...');
      this.loadUsers();  // ← Make sure this line exists and works
      
      this.snackBar.open(
        `User updated successfully!`, 
        'Close', 
        { duration: 3000 }
      );
    }
  });
}

  onToggleUserStatus(user: User) {
    console.log('Toggle status for user:', user);
    
    if (user.is_active) {
      // User is active - show deactivation confirmation
      const action = window.confirm(
        `Are you sure you want to deactivate user "${user.email}"?\n\n` +
        `This will:\n` +
        `• Prevent them from logging in\n` +
        `• Keep their data for potential reactivation\n` +
        `• Can be undone later\n\n` +
        `Click OK to deactivate or Cancel to abort.`
      );
      
      if (action) {
        // User confirmed deactivation
        this.superAdminService.deleteUser(user._id, 'soft').subscribe({
          next: (response: any) => {
            if (response.success) {
              console.log('✅ User deactivated:', response);
              this.snackBar.open(
                `User "${user.email}" has been deactivated successfully!`, 
                'Close', 
                { duration: 5000 }
              );
              this.loadUsers(); // Refresh the user list
            } else {
              console.error('❌ Deactivation failed:', response);
              this.snackBar.open(
                `Failed to deactivate user: ${response.error}`, 
                'Close', 
                { duration: 5000 }
              );
            }
          },
          error: (error: any) => {
            console.error('❌ Error deactivating user:', error);
            this.snackBar.open(
              `Error deactivating user: ${error.message}`, 
              'Close', 
              { duration: 5000 }
            );
          }
        });
      }
    } else {
      // User is inactive - show reactivation confirmation
      const action = window.confirm(
        `Are you sure you want to reactivate user "${user.email}"?\n\n` +
        `This will:\n` +
        `• Allow them to log in again\n` +
        `• Restore their access permissions\n` +
        `• Make them active in the system\n\n` +
        `Click OK to reactivate or Cancel to abort.`
      );
      
      if (action) {
        // User confirmed reactivation
        this.superAdminService.reactivateUser(user._id).subscribe({
          next: (response: any) => {
            if (response.success) {
              console.log('✅ User reactivated:', response);
              this.snackBar.open(
                `User "${user.email}" has been reactivated successfully!`, 
                'Close', 
                { duration: 5000 }
              );
              this.loadUsers(); // Refresh the user list
            } else {
              console.error('❌ Reactivation failed:', response);
              this.snackBar.open(
                `Failed to reactivate user: ${response.error}`, 
                'Close', 
                { duration: 5000 }
              );
            }
          },
          error: (error: any) => {
            console.error('❌ Error reactivating user:', error);
            this.snackBar.open(
              `Error reactivating user: ${error.message}`, 
              'Close', 
              { duration: 5000 }
            );
          }
        });
      }
    }
  }

  onViewUserDetails(user: User) {
    console.log('View user details:', user);
    this.snackBar.open(`View details for ${user.email} will be implemented next!`, 'Close', {
      duration: 3000
    });
  }
}