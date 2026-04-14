// admin-portal.component.ts - OPTIMIZED VERSION
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../../services/admin.service';
import { SidebarComponent } from './sidebar/sidebar.component';
import { NavbarComponent } from './navbar/navbar.component';
import { DashboardComponent } from './dashboard/dashboard.component';
import { LeadsComponent } from './leads/leads.component';
import { ChatSessionComponent } from './chat-session/chat-session.component';
import { UniversitiesComponent } from './universities/universities.component';
import { ActivatedRoute, Router } from '@angular/router';
import { MarkdownPipe } from '../chatbot/markdown.pipe';

export interface Lead {
  _id: string;
  name: string;
  email: string;
  country: string;
  mobile: string;
  university_code: string;
  university_x_id?: string;
  created_at: string;
  updated_at?: string;
  live_chat_summaries?: LiveChatSummary[];
  chat_sessions?: string[];
  status?: string;
  lead_type?: 'hot' | 'cold' | 'not_defined';
  categorization_notes?: string;
  engagement_score?: number;
  last_interaction?: string;
}

export interface LiveChatSummary {
  session_id: string;
  user_message: string;
  assistant_response: string;
  timestamp: string;
  metadata?: any;
}

export interface ChatSession {
  _id: string;
  lead_id?: string;
  lead_name?: string;
  lead_email?: string;
  university_code: string;
  university_x_id?: string;
  university_name?: string;
  messages: ChatMessage[];
  message_count: number;
  created_at: string;
  updated_at?: string;
  duration?: string;
  topics?: string[];
  is_active: boolean;
  user_id?: string;
  metadata?: any;
}

export interface ChatMessage {
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface University {
  _id: string;
  name: string;
  code: string;
  x_id: string;
  document_count: number;
  description?: string;
  created_at: string;
  stats?: {
    total_leads?: number;
    total_sessions?: number;
    active_sessions?: number;
  };
}

export interface CategorizationStats {
  hot: number;
  cold: number;
  not_defined: number;
  total: number;
  breakdown?: {
    hot_percentage: number;
    cold_percentage: number;
    not_defined_percentage: number;
  };
}

@Component({
  selector: 'app-admin-portal',
  standalone: true,
  imports: [CommonModule, FormsModule, SidebarComponent, NavbarComponent, DashboardComponent, LeadsComponent, ChatSessionComponent, UniversitiesComponent, MarkdownPipe],
  templateUrl: './admin-portal.component.html',
  styleUrls: ['./admin-portal.component.scss']
})
export class AdminPortalComponent implements OnInit {
  adminUniversityContext: any = null;
  currentUniversity: University | null = null;
  activeTab: string = 'leads';
  leads: Lead[] = [];
  chatSessions: ChatSession[] = [];
  universities: University[] = [];
  selectedLead: Lead | null = null;
  selectedSession: ChatSession | null = null;
  searchTerm: string = '';
  loading: boolean = false;
  error: string = '';
  sidebarCollapsed: boolean = false;
  sidebarOpen: boolean = false;
  isMobileView: boolean = false;

  // Dashboard stats
  totalLeads: number = 0;
  totalSessions: number = 0;
  totalDocuments: number = 0;
  todaySessions: number = 0;

  // NEW PROPERTIES for categorization
  categorizationStats: CategorizationStats = {
    hot: 0,
    cold: 0,
    not_defined: 0,
    total: 0
  };

  constructor(
    private adminService: AdminService,
    private route: ActivatedRoute,
    private router: Router
  ) {
    this.checkMobileView();
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', () => this.checkMobileView());
    }
  }

  ngOnInit(): void {
    // Get admin's university context
    const universityContext = localStorage.getItem('adminUniversityContext');
    if (universityContext) {
      this.adminUniversityContext = JSON.parse(universityContext);
      console.log('Admin assigned to university:', this.adminUniversityContext);
    }

    // Listen to route data changes to set active tab
    this.route.data.subscribe(data => {
      if (data['activeTab']) {
        this.activeTab = data['activeTab'];
      }
    });

    this.loadDashboardData();
  }

  async loadDashboardData(): Promise<void> {
    this.loading = true;
    this.error = '';

    // ✅ CRITICAL: University context validation
    const adminUniversityContext = JSON.parse(localStorage.getItem('adminUniversityContext') || 'null');
    if (!adminUniversityContext) {
      this.error = 'No university assignment found. Please contact SuperAdmin.';
      this.loading = false;
      console.error('❌ Admin not assigned to any university');
      return;
    }

    console.log('🏛️ Loading dashboard data for university:', adminUniversityContext);
    console.log('🆔 University X-ID:', adminUniversityContext.x_id);
    console.log('🏢 University Code:', adminUniversityContext.code);

    try {
      // ✅ LOAD: Basic data first
      const [leadsResponse, universitiesResponse] = await Promise.all([
        this.adminService.getLeads().toPromise(),
        this.adminService.getUniversities().toPromise()
      ]);
      
      // ✅ FILTER: Only process leads for this admin's university
      const allLeads = leadsResponse?.leads || [];
      this.leads = allLeads.filter((lead: Lead) => {
        return lead.university_code?.toLowerCase() === adminUniversityContext.code.toLowerCase();
      });

      console.log(`📊 Filtered leads: ${this.leads.length} out of ${allLeads.length} total leads`);
      
      // ✅ FILTER: Only show current university in universities list
      const allUniversities = universitiesResponse?.universities || universitiesResponse || [];
      this.universities = allUniversities.filter((uni: University) => {
        return uni.x_id === adminUniversityContext.x_id;
      });

      console.log(`🏛️ Current university:`, this.universities[0]?.name || 'Not found');
      
      // ✅ LOAD: Chat sessions (DATABASE FIRST, LEADS AS FALLBACK)
      await this.loadChatSessions(adminUniversityContext.x_id);
      
      // ✅ CALCULATE: University-specific stats
      this.calculateStats();
      
      this.loading = false;

      this.loadCategorizationStats();
      
      console.log('✅ Dashboard data loaded successfully');
      console.log(`📈 Final Stats: ${this.totalLeads} leads, ${this.totalSessions} sessions, ${this.totalDocuments} documents`);
      
    } catch (error) {
      console.error('❌ Error loading dashboard data:', error);
      this.error = 'Failed to load dashboard data. Please check your connection.';
      this.loading = false;
    }
  }

  private async loadChatSessions(universityXId: string): Promise<void> {
    // Initialize empty sessions array
    this.chatSessions = [];
    
    try {
      console.log(`🔍 Loading chat sessions for university X-ID: ${universityXId}`);
      
      // Try to load from database first
      const chatSessionsResponse = await this.adminService.getUniversitySessions(universityXId, 1000).toPromise();
      
      console.log('📥 Chat sessions response:', chatSessionsResponse);
      
      if (chatSessionsResponse?.sessions?.length > 0) {
        // ✅ SUCCESS: Load database sessions
        this.loadDatabaseSessions(chatSessionsResponse.sessions);
        console.log(`✅ Loaded ${chatSessionsResponse.sessions.length} sessions from database`);
      } else {
        // ✅ FALLBACK: Load from lead summaries
        console.warn('⚠️ No database sessions found, falling back to lead summaries');
        this.loadLeadSummariesSessions();
      }
      
    } catch (error) {
      console.error('⚠️ Error loading database sessions:', error);
      // ✅ FALLBACK: Load from lead summaries
      console.log('🔄 Falling back to lead summaries...');
      this.loadLeadSummariesSessions();
    }
  }

  private loadDatabaseSessions(sessions: any[]): void {
    console.log(`💬 Processing ${sessions.length} database sessions`);
    
    this.chatSessions = sessions.map((session: any) => ({
      _id: session._id,
      lead_id: session.lead_id || null,
      lead_name: session.lead_name || 'Unknown',
      lead_email: session.lead_email || '',
      university_code: session.university_code,
      university_x_id: session.university_x_id,
      university_name: session.university_name,
      messages: [], // Will be loaded on demand
      message_count: session.message_count || 0,
      created_at: session.created_at,
      updated_at: session.updated_at,
      is_active: session.is_active || false,
      user_id: session.user_id,
      metadata: session.metadata || {},
      topics: this.extractTopicsFromSession(session)
    }));
    
    console.log(`✅ Database sessions processed: ${this.chatSessions.length} sessions`);
  }

  private loadLeadSummariesSessions(): void {
    console.log('🔄 Processing chat sessions from lead summaries');
    
    const leadSessions: ChatSession[] = [];
    
    this.leads.forEach((lead: Lead) => {
      if (lead.live_chat_summaries?.length) {
        lead.live_chat_summaries.forEach((summary: LiveChatSummary) => {
          if (summary.user_message && summary.assistant_response && summary.timestamp) {
            leadSessions.push({
              _id: summary.session_id || `lead_${lead._id}_${Date.now()}_${Math.random()}`,
              lead_id: lead._id,
              lead_name: lead.name,
              lead_email: lead.email,
              university_code: lead.university_code,
              messages: [
                {
                  type: 'user',
                  content: summary.user_message,
                  timestamp: summary.timestamp
                },
                {
                  type: 'assistant',
                  content: summary.assistant_response,
                  timestamp: summary.timestamp
                }
              ],
              message_count: 2,
              created_at: summary.timestamp,
              is_active: false,
              topics: this.extractTopics([
                { type: 'user', content: summary.user_message, timestamp: summary.timestamp },
                { type: 'assistant', content: summary.assistant_response, timestamp: summary.timestamp }
              ]),
              metadata: summary.metadata || {}
            });
          }
        });
      }
    });

    this.chatSessions = leadSessions;
    console.log(`✅ Lead summary sessions processed: ${this.chatSessions.length} sessions`);
  }

  private calculateStats(): void {
    this.totalLeads = this.leads.length;
    this.totalSessions = this.chatSessions.length;
    this.totalDocuments = this.universities.reduce((sum: number, uni: any) => sum + (uni.document_count || 0), 0);
    
    const today = new Date().toDateString();
    this.todaySessions = this.chatSessions.filter((session: ChatSession) => {
      return new Date(session.created_at).toDateString() === today;
    }).length;
  }

  private extractTopicsFromSession(session: any): string[] {
    if (session.metadata?.topics) {
      return session.metadata.topics;
    }
    return ['General Inquiry'];
  }

  extractTopics(messages: ChatMessage[]): string[] {
    const topics: string[] = [];
    const text = messages.map(m => m.content || '').join(' ').toLowerCase();
    
    if (text.includes('admission') || text.includes('apply')) topics.push('Admissions');
    if (text.includes('program') || text.includes('course') || text.includes('degree')) topics.push('Programs');
    if (text.includes('fee') || text.includes('cost') || text.includes('tuition')) topics.push('Fees');
    if (text.includes('facility') || text.includes('campus')) topics.push('Facilities');
    if (text.includes('scholarship')) topics.push('Scholarships');
    if (text.includes('visa')) topics.push('Visa');
    
    return topics.length > 0 ? topics : ['General Inquiry'];
  }

  // GETTERS
  get filteredLeads(): Lead[] {
    if (!this.searchTerm) return this.leads;
    
    return this.leads.filter(lead =>
      lead.name.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
      lead.email.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
      lead.country.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
      lead.university_code.toLowerCase().includes(this.searchTerm.toLowerCase())
    );
  }

  get filteredSessions(): ChatSession[] {
    if (!this.searchTerm) return this.chatSessions;
    
    return this.chatSessions.filter(session =>
      session.lead_name?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
      session.lead_email?.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
      session.university_code.toLowerCase().includes(this.searchTerm.toLowerCase())
    );
  }

  // TAB MANAGEMENT
  setActiveTab(tab: string): void {
    this.router.navigate(['/admin', tab]);
  }

  onTabChange(tab: string): void {
    this.router.navigate(['/admin', tab]);
  }

  // SELECTION METHODS
  selectLead(lead: Lead): void {
    this.selectedLead = lead;
  }

  selectSession(session: ChatSession): void {
    this.selectedSession = session;
    
    if (session._id && session._id.startsWith('session_')) {
      this.loadFullSessionDetails(session._id);
    }
  }

  private loadFullSessionDetails(sessionId: string): void {
    this.adminService.getChatHistory(sessionId).subscribe({
      next: (response) => {
        if (this.selectedSession && response.messages) {
          this.selectedSession.messages = response.messages;
          this.selectedSession.message_count = response.messages.length;
        }
      },
      error: (error) => {
        console.error('Error loading session details:', error);
      }
    });
  }

  closeModal(): void {
    this.selectedLead = null;
    this.selectedSession = null;
  }

  // EXPORT METHODS
  exportLeads(): void {
    try {
      const leadsData = this.leads.map(lead => ({
        name: lead.name,
        email: lead.email,
        country: lead.country,
        mobile: lead.mobile || '',
        university: lead.university_code,
        created_date: new Date(lead.created_at).toLocaleDateString(),
        sessions_count: lead.live_chat_summaries?.length || 0
      }));

      const csvContent = this.generateCSVContent(leadsData, [
        'name', 'email', 'country', 'mobile', 'university', 'created_date', 'sessions_count'
      ]);
      
      this.downloadCSV(csvContent, 'leads-export.csv');
    } catch (error) {
      console.error('Error exporting leads:', error);
      this.error = 'Failed to export leads';
    }
  }

  exportSessions(): void {
    try {
      const sessionsData = this.chatSessions.map(session => ({
        session_id: session._id,
        lead_name: session.lead_name || '',
        lead_email: session.lead_email || '',
        university: session.university_code,
        messages: session.message_count,
        date: new Date(session.created_at).toLocaleDateString(),
        topics: session.topics?.join('; ') || ''
      }));

      const csvContent = this.generateCSVContent(sessionsData, [
        'session_id', 'lead_name', 'lead_email', 'university', 'messages', 'date', 'topics'
      ]);
      
      this.downloadCSV(csvContent, 'sessions-export.csv');
    } catch (error) {
      console.error('Error exporting sessions:', error);
      this.error = 'Failed to export sessions';
    }
  }

  private generateCSVContent(data: any[], headers: string[]): string {
    const csvHeaders = headers.map(h => h.replace('_', ' ').toUpperCase());
    const rows = data.map(item => 
      headers.map(header => {
        const value = item[header];
        if (Array.isArray(value)) {
          return value.join('; ');
        }
        return value || '';
      })
    );

    return [csvHeaders, ...rows].map(row => 
      row.map(cell => `"${cell}"`).join(',')
    ).join('\n');
  }

  private downloadCSV(content: string, filename: string): void {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }

  // UTILITY METHODS
  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString();
  }

  getSessionDuration(session: ChatSession): string {
    const estimatedMinutes = session.message_count * 1.5;
    return `~${Math.round(estimatedMinutes)} min`;
  }

  refreshData(): void {
    this.loadDashboardData();
  }

  getUniversityName(code: string): string {
    const university = this.universities.find(uni => uni.code === code);
    return university ? university.name : code.toUpperCase();
  }

  // SIDEBAR MANAGEMENT
  onSidebarToggle(): void {
    if (this.isMobileView) {
      this.sidebarOpen = !this.sidebarOpen;
    } else {
      this.sidebarCollapsed = !this.sidebarCollapsed;
      localStorage.setItem('sidebar_collapsed', String(this.sidebarCollapsed));
    }
  }

  closeSidebar(): void {
    this.sidebarOpen = false;
  }

  private checkMobileView(): void {
    if (typeof window !== 'undefined') {
      this.isMobileView = window.innerWidth <= 768;
      
      if (!this.isMobileView && this.sidebarOpen) {
        this.sidebarOpen = false;
      }
    }
  }

  // EVENT HANDLERS
  onDashboardTabChange(tab: string): void {
    this.router.navigate(['/admin', tab]);
  }

  onDashboardExportLeads(): void {
    this.exportLeads();
  }

  onLeadSelect(lead: any): void {
    this.selectedLead = lead;
  }

  onLeadsExport(): void {
    this.exportLeads();
  }

  onLeadSearchChange(searchTerm: string): void {
    this.searchTerm = searchTerm;
  }

  onSessionSelect(session: any): void {
    this.selectedSession = session;
  }

  onSessionsExport(): void {
    this.exportSessions();
  }

  onSessionSearchChange(searchTerm: string): void {
    this.searchTerm = searchTerm;
  }

  onRefreshClick(): void {
    this.refreshData();
  }

  // UNIVERSITY MANAGEMENT METHODS
  onManageUniversityDocuments(university: any): void {
    this.manageUniversityDocuments(university);
  }

  onLoadUniversityStats(university: any): void {
    this.loadUniversityStats(university);
  }

  loadUniversityStats(university: University): void {
    if (university.x_id) {
      this.adminService.getUniversityStats(university.x_id).subscribe({
        next: (stats) => {
          university.stats = {
            total_leads: this.leads.filter(l => l.university_code === university.code).length,
            total_sessions: this.chatSessions.filter(s => s.university_code === university.code).length,
            active_sessions: this.chatSessions.filter(s => 
              s.university_code === university.code && s.is_active
            ).length
          };
        },
        error: (error) => {
          console.error('Error loading university stats:', error);
        }
      });
    }
  }

  manageUniversityDocuments(university: University): void {
    // This would open a document management modal or navigate to document management
    console.log('Managing documents for:', university.name);
    // TODO: Implement document management functionality
  }

  getPageTitle(): string {
    switch (this.activeTab) {
      case 'dashboard':
        return 'Dashboard';
      case 'leads':
        return 'Lead Management';
      case 'sessions':
        return 'Chat Sessions';
      case 'universities':
        return 'Universities';
      default:
        return 'Admin Portal';
    }
  }

  onLogout(): void {
    console.log('Admin logout requested');
    
    // Clear all stored data
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    localStorage.removeItem('adminUniversityContext');
    
    // Navigate to login page
    this.router.navigate(['/auth/login']);
  }

  // DEBUG METHODS (Keep for troubleshooting)
  debugUniversityContext(): void {
    const context = JSON.parse(localStorage.getItem('adminUniversityContext') || 'null');
    console.log('🔍 DEBUG: Admin University Context:', context);
  }

  async testUniversitySessionsAPI(): Promise<void> {
    const context = JSON.parse(localStorage.getItem('adminUniversityContext') || 'null');
    if (!context) {
      console.error('❌ No university context');
      return;
    }
    
    try {
      const response = await this.adminService.getUniversitySessions(context.x_id, 500).toPromise();
      console.log('✅ API Response:', response);
      console.log('📊 Sessions Count:', response?.sessions?.length || 0);
    } catch (error) {
      console.error('❌ API Error:', error);
    }
  }

  compareSessions(): void {
    console.log('📊 Lead-based sessions:', this.chatSessions.filter(s => s._id.includes('lead_')).length);
    console.log('📊 Database sessions:', this.chatSessions.filter(s => !s._id.includes('lead_')).length);
    console.log('📊 Total sessions:', this.chatSessions.length);
  }

  // NEW METHOD: Update lead categorization
  updateLeadCategorization(leadId: string, leadType: string, notes?: string): void {

     const validLeadTypes = ['hot', 'cold', 'not_defined'];
  if (!validLeadTypes.includes(leadType)) {
    console.error('Invalid lead type:', leadType);
    return;
  }
    this.adminService.updateLeadCategorization(leadId, leadType, notes).subscribe({
      next: (response) => {
        if (response.success) {
          // Update the lead in the local array
          const leadIndex = this.leads.findIndex(lead => lead._id === leadId);
          if (leadIndex !== -1) {
            this.leads[leadIndex].lead_type = leadType as 'hot' | 'cold' | 'not_defined';
            this.leads[leadIndex].categorization_notes = notes;
            this.leads[leadIndex].updated_at = new Date().toISOString();
          }
          
          // Refresh categorization stats
          this.loadCategorizationStats();
          
          console.log('Lead categorization updated successfully');
        }
      },
      error: (error) => {
        console.error('Error updating lead categorization:', error);
      }
    });
  }

  // NEW METHOD: Load categorization statistics
  loadCategorizationStats(): void {
     console.log('📊 Loading categorization stats...');
    this.adminService.getCategorizationStats().subscribe({
      next: (response) => {
        console.log('📊 API Response:', response);
        if (response.success) {
          this.categorizationStats = response.categorization_stats;
          console.log('📊 Updated categorization stats:', this.categorizationStats);
          if (response.breakdown) {
            this.categorizationStats.breakdown = response.breakdown;
          }
        }
      },
      error: (error) => {
        console.error('Error loading categorization stats:', error);
        // Keep default stats on error
      }
    });
  }

  // NEW METHOD: Get lead type display name
  getLeadTypeDisplay(leadType?: string): string {
    const typeMap = {
      'hot': 'Hot Lead',
      'cold': 'Cold Lead',
      'not_defined': 'Not Defined'
    };
    return typeMap[leadType as keyof typeof typeMap] || 'Not Defined';
  }

  // NEW METHOD: Get lead type CSS class
  getLeadTypeClass(leadType?: string): string {
    const classMap = {
      'hot': 'lead-type-hot',
      'cold': 'lead-type-cold',
      'not_defined': 'lead-type-not-defined'
    };
    return classMap[leadType as keyof typeof classMap] || 'lead-type-not-defined';
  }
}
