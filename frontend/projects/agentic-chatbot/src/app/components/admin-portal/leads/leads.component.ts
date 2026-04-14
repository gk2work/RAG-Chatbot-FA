import { Component, Input, Output, EventEmitter, ViewChild, OnChanges, AfterViewInit, OnInit} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MaterialModule } from '../../../shared/material.module';
import { MatTableDataSource } from '@angular/material/table';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';

@Component({
  selector: 'app-leads',
  standalone: true,
  imports: [CommonModule, FormsModule, MaterialModule],
  templateUrl: './leads.component.html',
  styleUrl: './leads.component.scss'
})
export class LeadsComponent implements OnInit, OnChanges, AfterViewInit {

  @Input() leads: any[] = [];
  @Input() searchTerm: string = '';

  @Output() leadSelect = new EventEmitter<any>();
  @Output() exportLeads = new EventEmitter<void>();
  @Output() searchTermChange = new EventEmitter<string>();
  
  // NEW: Categorization output
  @Output() categorizationUpdate = new EventEmitter<{
    leadId: string;
    leadType: string;
    notes: string;
  }>();

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  selectedLead: any = null;
  dataSource = new MatTableDataSource<any>([]);
  displayedColumns: string[] = ['avatar', 'email', 'country', 'university', 'sessions', 'category', 'created', 'actions'];

  // NEW: Categorization properties
  selectedCategory: string = 'all';
  showCategorizationModal: boolean = false;
  leadBeingCategorized: any = null;
  categorizationForm = {
    leadType: 'not_defined',
    notes: ''
  };

  // NEW: Category options
  categoryOptions = [
    { value: 'all', label: 'All Leads', count: 0 },
    { value: 'hot', label: 'Hot Leads', count: 0, color: 'var(--lead-hot-color)' },
    { value: 'cold', label: 'Cold Leads', count: 0, color: 'var(--lead-cold-color)' },
    { value: 'not_defined', label: 'Not Defined', count: 0, color: 'var(--lead-undefined-color)' }
  ];

  get filteredLeads(): any[] {
    let filtered = this.leads;

    // Apply category filter first
    if (this.selectedCategory !== 'all') {
      filtered = filtered.filter(lead => 
        (lead.lead_type || 'not_defined') === this.selectedCategory
      );
    }

    // Apply search filter
    if (this.searchTerm) {
      filtered = filtered.filter(lead =>
        lead.name.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        lead.email.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        lead.country.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        lead.university_code.toLowerCase().includes(this.searchTerm.toLowerCase())
      );
    }

    return filtered;
  }

  ngOnInit(): void {
    if (this.leads && this.leads.length > 0) {
      this.updateDataSource();
    }
    this.updateCategoryCounts();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
    this.setupFilter();
  }

  ngOnChanges(): void {
    console.log('ngOnChanges called with leads:', this.leads);

    if (this.leads && this.leads.length > 0) {
      this.updateDataSource();
    } else {
      this.dataSource.data = [];
    }
    this.updateCategoryCounts();
  }

  private updateDataSource(): void {
    // Use filtered leads instead of all leads for the data source
    this.dataSource.data = this.filteredLeads || [];
    console.log('Data Source updated with:', this.dataSource.data.length, 'leads');

    // Refresh paginator after data update
    if (this.paginator) {
      this.paginator.firstPage();
    }
    if (this.searchTerm) {
      this.applyFilter();
    }
  }

  private applyFilter(): void {
    const filterValue = this.searchTerm.trim().toLowerCase();
    this.dataSource.filter = filterValue;
    
    // Reset to first page when applying filter
    if (this.dataSource.paginator) {
      this.dataSource.paginator.firstPage();
    }
  }

  private setupFilter(): void {
    this.dataSource.filterPredicate = (data: any, filter: string) => {
      const searchStr = (
        data.name + 
        data.email + 
        data.country + 
        data.university_code
      ).toLowerCase();
      
      return searchStr.includes(filter);
    };
  }

  onSearchChange(): void {
    this.searchTermChange.emit(this.searchTerm);
    this.updateDataSource(); // Update data source when search changes
  }

  // NEW: Handle category filter change
  onCategoryFilterChange(category: string): void {
    this.selectedCategory = category;
    this.updateDataSource(); // Update data source when category changes
  }

  // NEW: Update category counts
  updateCategoryCounts(): void {
    this.categoryOptions[0].count = this.leads.length; // All leads
    this.categoryOptions[1].count = this.leads.filter(lead => lead.lead_type === 'hot').length;
    this.categoryOptions[2].count = this.leads.filter(lead => lead.lead_type === 'cold').length;
    this.categoryOptions[3].count = this.leads.filter(lead => (lead.lead_type || 'not_defined') === 'not_defined').length;
  }

  selectLead(lead: any): void {
    this.selectedLead = lead;
    this.leadSelect.emit(lead);
  }

  closeModal(): void {
    this.selectedLead = null;
  }

  onExportLeads(): void {
    this.exportLeads.emit();
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString();
  }

  // NEW: Open categorization modal
  openCategorizationModal(lead: any): void {
    this.leadBeingCategorized = lead;
    this.categorizationForm.leadType = lead.lead_type || 'not_defined';
    this.categorizationForm.notes = lead.categorization_notes || '';
    this.showCategorizationModal = true;
  }

  // NEW: Close categorization modal
  closeCategorizationModal(): void {
    this.showCategorizationModal = false;
    this.leadBeingCategorized = null;
    this.categorizationForm = {
      leadType: 'not_defined',
      notes: ''
    };
  }

  // NEW: Save lead categorization
  saveLeadCategorization(): void {
    if (!this.leadBeingCategorized) return;

    // Emit categorization update to parent component
    this.categorizationUpdate.emit({
      leadId: this.leadBeingCategorized._id,
      leadType: this.categorizationForm.leadType,
      notes: this.categorizationForm.notes
    });

    // Update local lead data optimistically
    const leadIndex = this.leads.findIndex(lead => lead._id === this.leadBeingCategorized._id);
    if (leadIndex !== -1) {
      this.leads[leadIndex].lead_type = this.categorizationForm.leadType;
      this.leads[leadIndex].categorization_notes = this.categorizationForm.notes;
      this.leads[leadIndex].updated_at = new Date().toISOString();
    }

    // Update category counts and data source
    this.updateCategoryCounts();
    this.updateDataSource();

    // Close modal
    this.closeCategorizationModal();
  }

  // NEW: Quick categorization methods
  quickCategorizeAsHot(lead: any): void {
    this.categorizationUpdate.emit({
      leadId: lead._id,
      leadType: 'hot',
      notes: 'Quick categorized as hot lead'
    });
    
    // Update local data
    const leadIndex = this.leads.findIndex(l => l._id === lead._id);
    if (leadIndex !== -1) {
      this.leads[leadIndex].lead_type = 'hot';
      this.updateCategoryCounts();
      this.updateDataSource();
    }
  }

  quickCategorizeAsCold(lead: any): void {
    this.categorizationUpdate.emit({
      leadId: lead._id,
      leadType: 'cold',
      notes: 'Quick categorized as cold lead'
    });
    
    // Update local data
    const leadIndex = this.leads.findIndex(l => l._id === lead._id);
    if (leadIndex !== -1) {
      this.leads[leadIndex].lead_type = 'cold';
      this.updateCategoryCounts();
      this.updateDataSource();
    }
  }

  // NEW: Get lead type display
  getLeadTypeDisplay(leadType?: string): string {
    const typeMap = {
      'hot': 'Hot Lead',
      'cold': 'Cold Lead',
      'not_defined': 'Not Defined'
    };
    return typeMap[leadType as keyof typeof typeMap] || 'Not Defined';
  }

  // NEW: Get lead type class for styling
  getLeadTypeClass(leadType?: string): string {
    return `lead-type-${leadType || 'not-defined'}`;
  }

  // NEW: Get lead type badge class (CSS handles the styling)
  getLeadTypeBadgeClass(leadType?: string): string {
    const baseClass = 'lead-badge';
    const typeClass = leadType ? `lead-badge-${leadType}` : 'lead-badge-not-defined';
    return `${baseClass} ${typeClass}`;
  }
}