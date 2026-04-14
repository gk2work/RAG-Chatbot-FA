// super-admin-analytics.component.ts
import { Component, OnInit, ViewChild, ElementRef, AfterViewInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Chart, ChartConfiguration, ChartType, registerables } from 'chart.js';
import { SuperAdminService, AnalyticsData } from '../../../services/super-admin.service';
import { AnalyticsWebSocketService } from '../../../services/analytics-websocket.service';
import { MatChipsModule } from '@angular/material/chips';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

// Register Chart.js components
Chart.register(...registerables);


@Component({
  selector: 'app-super-admin-analytics',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatFormFieldModule,
    MatSnackBarModule,
    MatChipsModule
  ],
  templateUrl: './super-admin-analytics.component.html',
  styleUrls: ['./super-admin-analytics.component.scss']
})
export class SuperAdminAnalyticsComponent implements OnInit, OnDestroy {
  @ViewChild('leadsChart', { static: false }) leadsChartRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('sessionsChart', { static: false }) sessionsChartRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('countriesChart', { static: false }) countriesChartRef!: ElementRef<HTMLCanvasElement>;

  loading = true;
  error = '';
  analyticsData: AnalyticsData | null = null;
  
  // Chart instances
  leadsChart: Chart | null = null;
  sessionsChart: Chart | null = null;
  countriesChart: Chart | null = null;

  // Real-time status properties
  isConnected = false;
  lastUpdateTime: Date | null = null;
  updateCount = 0;
  
  // Filter options
  selectedDays = 30;
  dayOptions = [
    { value: 7, label: 'Last 7 days' },
    { value: 30, label: 'Last 30 days' },
    { value: 90, label: 'Last 90 days' }
  ];

  constructor(
    private snackBar: MatSnackBar,
    private superAdminService: SuperAdminService,
    private analyticsWebSocket: AnalyticsWebSocketService
  ) {}

  ngOnInit() {
    this.loadAnalyticsData();
    this.subscribeToRealTimeUpdates();
    this.startDemoUpdates();
  }

  ngAfterViewInit() {
    // Charts will be created after data is loaded
  }

  loadAnalyticsData() {
    this.loading = true;
    this.error = '';
    
    this.superAdminService.getAnalytics().subscribe({
      next: (response: AnalyticsData) => {
        this.analyticsData = response;
        this.loading = false;
        this.loadUniversitiesData();
      },
      error: (error: any) => {
        console.error('Error loading analytics:', error);
        this.error = 'Failed to load analytics data';
        this.loading = false;
      }
    });
  }
loadUniversitiesData() {
  this.superAdminService.getUniversities().subscribe({
    next: (universitiesResponse: any) => {
      if (this.analyticsData && universitiesResponse.success) {
        const universities = universitiesResponse.universities || [];
        
        // Populate leads by university
        this.analyticsData.data.leads.by_university = universities.map((uni: any) => ({
          _id: uni.x_id,
          count: Math.floor(Math.random() * 100) + 20, // Mock data for now
          university_name: uni.name
        }));
        
        // Populate sessions by university  
        this.analyticsData.data.sessions.by_university = universities.map((uni: any) => ({
          _id: uni.x_id,
          count: Math.floor(Math.random() * 200) + 50, // Mock data for now
          avg_messages: Math.floor(Math.random() * 10) + 3, // Mock data for now
          university_name: uni.name
        }));
        
        // Populate users by university
        this.analyticsData.data.users.by_university = universities.map((uni: any) => ({
          _id: uni.x_id,
          total_users: Math.floor(Math.random() * 50) + 10, // Mock data for now
          admins: Math.floor(Math.random() * 5) + 1, // Mock data for now
          students: Math.floor(Math.random() * 45) + 5, // Mock data for now
          university_name: uni.name
        }));
      }
      
      this.loading = false;
      this.createCharts();
    },
    error: (error: any) => {
      console.error('Error loading universities:', error);
      this.loading = false;
      this.createCharts(); // Still create charts with available data
    }
  });
}

 startDemoUpdates() {
  console.log('🚀 Starting demo real-time updates...');
  
  // Simulate real-time updates every 10 seconds
  setInterval(() => {
    this.simulateRealTimeUpdate();
  }, 10000);
  
  // First update after 3 seconds
  setTimeout(() => {
    this.simulateRealTimeUpdate();
  }, 3000);
}

simulateRealTimeUpdate() {
  const updateTypes = ['new_lead', 'new_session', 'new_user'];
  const randomType = updateTypes[Math.floor(Math.random() * updateTypes.length)];
  
  const mockUpdate = {
    type: randomType,
    data: {
      university_x_id: 'XNR35QWNP', // Use existing university
      timestamp: new Date().toISOString()
    },
    timestamp: new Date().toISOString()
  };
  
  console.log('🎭 Simulating update:', mockUpdate);
  this.handleRealTimeUpdate(mockUpdate);
}
subscribeToRealTimeUpdates() {
  this.analyticsWebSocket.getAnalyticsUpdates().subscribe({
    next: (update) => {
      if (update) {
        console.log('📊 Received real-time update:', update);
        this.handleRealTimeUpdate(update);
        this.lastUpdateTime = new Date();
        this.updateCount += 1;
      }
    },
    error: (error) => {
      console.error('❌ WebSocket subscription error:', error);
    }
  });

  this.analyticsWebSocket.getConnectionStatus().subscribe({
    next: (connected) => {
      console.log('📡 WebSocket connection status:', connected);
      this.isConnected = connected;
      // For demo purposes, set to true until backend WebSocket is ready
if (!connected) {
  setTimeout(() => { this.isConnected = true; }, 2000);
}
    }
  });
}
 exportToCSV() {
  if (!this.analyticsData) {
    this.snackBar.open('No data available for export', 'Close', { duration: 3000 });
    return;
  }

  try {
    // Prepare analytics data for CSV export
    const analyticsCSVData = [
      // Summary data
      ['Analytics Summary', ''],
      ['Total Leads', this.analyticsData.data.leads.total],
      ['Total Sessions', this.analyticsData.data.sessions.total],
      ['Total Users', this.analyticsData.data.users.total],
      ['Export Date', new Date().toLocaleDateString()],
      ['Time Period', `Last ${this.selectedDays} days`],
      [''], // Empty row
      
      // Leads by University
      ['Leads by University', ''],
      ['University ID', 'University Name', 'Lead Count'],
      ...this.analyticsData.data.leads.by_university.map((uni: any) => [
        uni._id,
        uni.university_name,
        uni.count
      ]),
      [''], // Empty row
      
      // Sessions by University  
      ['Sessions by University', ''],
      ['University ID', 'University Name', 'Session Count', 'Avg Messages'],
      ...this.analyticsData.data.sessions.by_university.map((uni: any) => [
        uni._id, 
        uni.university_name,
        uni.count,
        uni.avg_messages
      ]),
      [''], // Empty row
      
      // Countries data
      ['Leads by Country', ''],
      ['Country', 'Lead Count'],
      ...this.analyticsData.data.leads.by_country.map((country: any) => [
        country._id,
        country.count
      ])
    ];

    const csvContent = this.generateCSVContent(analyticsCSVData);
    const filename = `analytics-report-${this.selectedDays}days-${new Date().toISOString().split('T')[0]}.csv`;
    
    this.downloadCSV(csvContent, filename);
    this.snackBar.open('Analytics report exported successfully!', 'Close', { duration: 3000 });
    
  } catch (error) {
    console.error('Error exporting analytics:', error);
    this.snackBar.open('Failed to export analytics', 'Close', { duration: 3000 });
  }
}

private generateCSVContent(data: any[]): string {
  return data.map(row => {
    if (Array.isArray(row)) {
      return row.map(cell => `"${cell}"`).join(',');
    } else {
      return `"${row}"`;
    }
  }).join('\n');
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
    URL.revokeObjectURL(url);
  }
}

async exportToPDF() {
  if (!this.analyticsData) {
    this.snackBar.open('No data available for export', 'Close', { duration: 3000 });
    return;
  }

  try {
    this.snackBar.open('Generating PDF report...', 'Close', { duration: 2000 });
    
    const pdf = new jsPDF();
    let yPosition = 20;
    
    // Add title
    pdf.setFontSize(20);
    pdf.text('Analytics Report', 20, yPosition);
    yPosition += 15;
    
    // Add summary info
    pdf.setFontSize(12);
    pdf.text(`Generated: ${new Date().toLocaleDateString()}`, 20, yPosition);
    yPosition += 8;
    pdf.text(`Time Period: Last ${this.selectedDays} days`, 20, yPosition);
    yPosition += 15;
    
    // Add summary statistics
    pdf.setFontSize(14);
    pdf.text('Summary Statistics', 20, yPosition);
    yPosition += 10;
    
    pdf.setFontSize(10);
    pdf.text(`Total Leads: ${this.analyticsData.data.leads.total}`, 20, yPosition);
    yPosition += 6;
    pdf.text(`Total Sessions: ${this.analyticsData.data.sessions.total}`, 20, yPosition);
    yPosition += 6;
    pdf.text(`Total Users: ${this.analyticsData.data.users.total}`, 20, yPosition);
    yPosition += 15;
    
    // Add university data table
    pdf.setFontSize(12);
    pdf.text('Leads by University', 20, yPosition);
    yPosition += 10;
    
    // Table headers
    pdf.setFontSize(9);
    pdf.text('University ID', 20, yPosition);
    pdf.text('University Name', 60, yPosition);
    pdf.text('Lead Count', 120, yPosition);
    yPosition += 8;
    
    // Table data
    this.analyticsData.data.leads.by_university.forEach((uni: any) => {
      pdf.text(uni._id, 20, yPosition);
      pdf.text(uni.university_name, 60, yPosition);
      pdf.text(uni.count.toString(), 120, yPosition);
      yPosition += 6;
    });

    // Add charts if available
    if (this.leadsChartRef) {
      yPosition += 10;
      pdf.addPage();
      yPosition = 20;
  
    pdf.setFontSize(14);
    pdf.text('Visual Analytics', 20, yPosition);
    yPosition += 15;
  
    // Capture and add leads chart
    const leadsChartImage = await this.captureChart(this.leadsChartRef);
    if (leadsChartImage) {
      pdf.text('Leads by University', 20, yPosition);
      yPosition += 10;
     pdf.addImage(leadsChartImage, 'PNG', 20, yPosition, 150, 100);
     yPosition += 110;
  }
}


    
   // Save PDF
    const filename = `analytics-report-${this.selectedDays}days-${new Date().toISOString().split('T')[0]}.pdf`;
    pdf.save(filename);
    
    this.snackBar.open('PDF report generated successfully!', 'Close', { duration: 3000 });
    
  } catch (error) {
    console.error('Error generating PDF:', error);
    this.snackBar.open('Failed to generate PDF report', 'Close', { duration: 3000 });
  }
}

private async captureChart(chartRef: ElementRef<HTMLCanvasElement>): Promise<string> {
  if (!chartRef?.nativeElement) {
    return '';
  }

  try {
    const canvas = await html2canvas(chartRef.nativeElement.parentElement!);
    return canvas.toDataURL('image/png');
  } catch (error) {
    console.error('Error capturing chart:', error);
    return '';
  }
}

handleRealTimeUpdate(update: any) {
  console.log('🔄 Processing real-time update:', update.type);
  
  switch (update.type) {
    case 'new_lead':
      this.updateLeadsData(update.data);
      break;
      
    case 'new_session':
      this.updateSessionsData(update.data);
      break;
      
    case 'new_user':
      this.updateUsersData(update.data);
      break;
      
    case 'analytics_update':
      this.refreshAnalyticsData();
      break;
      
    default:
      console.log('📊 Unknown update type:', update.type);
  }
}
updateLeadsData(leadData: any) {
  if (this.analyticsData?.data.leads) {
    // Increment total leads count
    this.analyticsData.data.leads.total += 1;
    this.analyticsData.data.leads.recent += 1;
    
    // Update university-specific lead count
    const universityData = this.analyticsData.data.leads.by_university.find(
      (uni: any) => uni._id === leadData.university_x_id
    );
    
    if (universityData) {
      universityData.count += 1;
    }
    
    console.log('📈 Updated leads data - New total:', this.analyticsData.data.leads.total);
    
    // Refresh the leads chart
    this.updateLeadsChart();
  }
}

updateSessionsData(sessionData: any) {
  if (this.analyticsData?.data.sessions) {
    // Increment total sessions count
    this.analyticsData.data.sessions.total += 1;
    this.analyticsData.data.sessions.recent += 1;
    
    // Update university-specific session count
    const universityData = this.analyticsData.data.sessions.by_university.find(
      (uni: any) => uni._id === sessionData.university_x_id
    );
    
    if (universityData) {
      universityData.count += 1;
    }
    
    console.log('💬 Updated sessions data - New total:', this.analyticsData.data.sessions.total);
    
    // Refresh the sessions chart
    this.updateSessionsChart();
  }
}

updateLeadsChart() {
  if (this.leadsChart && this.analyticsData?.data.leads) {
    const data = this.analyticsData.data.leads.by_university;
    
    // Update chart data
    this.leadsChart.data.labels = data.map((item: any) => item._id);
    this.leadsChart.data.datasets[0].data = data.map((item: any) => item.count);
    
    // Refresh the chart
    this.leadsChart.update('none'); // 'none' for instant update without animation
    
    console.log('📊 Leads chart updated');
  }
}

updateSessionsChart() {
  if (this.sessionsChart && this.analyticsData?.data.sessions) {
    const data = this.analyticsData.data.sessions.by_university;
    
    // Update chart data
    this.sessionsChart.data.labels = data.map((item: any) => item._id);
    this.sessionsChart.data.datasets[0].data = data.map((item: any) => item.count);
    this.sessionsChart.data.datasets[1].data = data.map((item: any) => item.avg_messages);
    
    // Refresh the chart
    this.sessionsChart.update('none');
    
    console.log('💬 Sessions chart updated');
  }
}

updateCountriesChart() {
  if (this.countriesChart && this.analyticsData?.data.leads) {
    const data = this.analyticsData.data.leads.by_country.slice(0, 5);
    
    // Update chart data
    this.countriesChart.data.labels = data.map((item: any) => item._id);
    this.countriesChart.data.datasets[0].data = data.map((item: any) => item.count);
    
    // Refresh the chart
    this.countriesChart.update('none');
    
    console.log('🌍 Countries chart updated');
  }
}

updateUsersData(userData: any) {
  if (this.analyticsData?.data.users) {
    // Increment total users count
    this.analyticsData.data.users.total += 1;
    
    console.log('👥 Updated users data - New total:', this.analyticsData.data.users.total);
  }
}

refreshAnalyticsData() {
  console.log('🔄 Refreshing all analytics data...');
  this.loadAnalyticsData();
}

  onDaysFilterChange() {
    console.log('Days filter changed to:', this.selectedDays);
    this.loadAnalyticsData();
  }

  refreshData() {
    console.log('Refreshing analytics data...');
    this.loadAnalyticsData();
  }

  createCharts() {
    if (!this.analyticsData) return;
    
    // Create charts after a short delay to ensure DOM elements are ready
    setTimeout(() => {
      this.createLeadsChart();
      this.createSessionsChart();
      this.createCountriesChart();
    }, 100);
  }

  createLeadsChart() {
    if (!this.leadsChartRef || !this.analyticsData) return;

    const ctx = this.leadsChartRef.nativeElement.getContext('2d');
    if (!ctx) return;

    const data = this.analyticsData.data.leads.by_university;
    
    this.leadsChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: data.map((item: any) => item._id),
        datasets: [{
          label: 'Leads',
          data: data.map((item: any) => item.count),
          backgroundColor: [
            '#1976d2',
            '#388e3c',
            '#f57c00',
            '#7b1fa2',
            '#c2185b'
          ],
          borderWidth: 2,
          borderColor: '#fff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom'
          },
          title: {
            display: true,
            text: 'Leads by University'
          }
        }
      }
    });
  }

  createSessionsChart() {
    if (!this.sessionsChartRef || !this.analyticsData) return;

    const ctx = this.sessionsChartRef.nativeElement.getContext('2d');
    if (!ctx) return;

    const data = this.analyticsData.data.sessions.by_university;
    
    this.sessionsChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map((item: any) => item._id),
        datasets: [{
          label: 'Total Sessions',
          data: data.map((item: any) => item.count),
          backgroundColor: 'rgba(25, 118, 210, 0.7)',
          borderColor: '#1976d2',
          borderWidth: 1
        }, {
          label: 'Avg Messages',
          data: data.map((item: any) => item.avg_messages),
          backgroundColor: 'rgba(56, 142, 60, 0.7)',
          borderColor: '#388e3c',
          borderWidth: 1,
          yAxisID: 'y1'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: {
            display: true,
            text: 'Sessions by University'
          }
        },
        scales: {
          y: {
            type: 'linear',
            display: true,
            position: 'left',
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            grid: {
              drawOnChartArea: false,
            },
          }
        }
      }
    });
  }

  createCountriesChart() {
    if (!this.countriesChartRef || !this.analyticsData) return;

    const ctx = this.countriesChartRef.nativeElement.getContext('2d');
    if (!ctx) return;

    const data = this.analyticsData.data.leads.by_country.slice(0, 5); // Top 5 countries
    
    this.countriesChart = new Chart(ctx, {
      type: 'bar' as ChartType,
      data: {
        labels: data.map((item: any) => item._id),
        datasets: [{
          label: 'Leads by Country',
          data: data.map((item: any) => item.count),
          backgroundColor: [
            '#1976d2',
            '#388e3c',
            '#f57c00',
            '#7b1fa2',
            '#c2185b'
          ],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          title: {
            display: true,
            text: 'Top Countries by Leads'
          },
          legend: {
            display: false
          }
        }
      }
    });
  }

  ngOnDestroy() {
    // Clean up charts
    if (this.leadsChart) this.leadsChart.destroy();
    if (this.sessionsChart) this.sessionsChart.destroy();
    if (this.countriesChart) this.countriesChart.destroy();
  }
}

