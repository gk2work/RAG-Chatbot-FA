import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Component, Input, Output, EventEmitter, ViewChild } from '@angular/core';
import { MaterialModule } from '../../../shared/material.module';
import { MatTableDataSource } from '@angular/material/table';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { MarkdownPipe } from '../../chatbot/markdown.pipe';


@Component({
  selector: 'app-chat-session',
  standalone: true,
  imports: [CommonModule, FormsModule, MaterialModule, MarkdownPipe],
  templateUrl: './chat-session.component.html',
  styleUrl: './chat-session.component.scss'
})
export class ChatSessionComponent {
  @Input() chatSessions: any[] = [];
  @Input() searchTerm: string = '';

  @Output() sessionSelect = new EventEmitter<any>();
  @Output() exportSessions = new EventEmitter<void>();
  @Output() searchTermChange = new EventEmitter<string>();

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  selectedSession: any = null;
  dataSource = new MatTableDataSource<any>([]);
  displayedColumns: string[] = ['session', 'lead', 'university', 'messages', 'duration', 'status', 'created', 'actions'];

  get filteredSessions(): any[] {
  if (!this.searchTerm) return this.chatSessions;
  
  return this.chatSessions.filter(session =>
    session.lead_name?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
    session.lead_email?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
    session.university_code.toLowerCase().includes(this.searchTerm.toLowerCase())
  );
}

onSearchChange(): void {
  this.searchTermChange.emit(this.searchTerm);
  this.applyFilter();
}

selectSession(session: any): void {
  this.selectedSession = session;
  this.sessionSelect.emit(session);
}

closeModal(): void {
  this.selectedSession = null;
}

onExportSessions(): void {
  this.exportSessions.emit();
}

getSessionDuration(session: any): string {
  const estimatedMinutes = session.message_count * 1.5;
  return `~${Math.round(estimatedMinutes)} min`;
}

formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString();
}
ngOnInit(): void {
  console.log('Chat sessions component initialized with:', this.chatSessions);
  if (this.chatSessions && this.chatSessions.length > 0) {
    this.updateDataSource();
  }
}

ngAfterViewInit(): void {
  this.dataSource.paginator = this.paginator;
  this.dataSource.sort = this.sort;
  this.setupFilter();
}

ngOnChanges(): void {
  console.log('ngOnChanges called with sessions:', this.chatSessions);
  
  if (this.chatSessions && this.chatSessions.length > 0) {
    this.updateDataSource();
  } else {
    this.dataSource.data = [];
  }
}

private updateDataSource(): void {
  this.dataSource.data = this.chatSessions || [];
  console.log('Session data source updated with:', this.dataSource.data.length, 'sessions');
  
  if (this.paginator) {
    this.paginator.firstPage();
  }
  
  if (this.searchTerm) {
    this.applyFilter();
  }
}

private setupFilter(): void {
  this.dataSource.filterPredicate = (data: any, filter: string) => {
    const searchStr = (
      (data.lead_name || '') + 
      (data.lead_email || '') + 
      data.university_code + 
      data._id
    ).toLowerCase();
    
    return searchStr.includes(filter);
  };
}

private applyFilter(): void {
  const filterValue = this.searchTerm.trim().toLowerCase();
  this.dataSource.filter = filterValue;
  
  if (this.dataSource.paginator) {
    this.dataSource.paginator.firstPage();
  }
}


}

