import {
  Component,
  OnInit,
  Input,
  Output,
  EventEmitter,
  ViewChild,
  ElementRef,
  AfterViewInit,
  OnDestroy,
  OnChanges,
} from "@angular/core";
import { Chart, ChartConfiguration, ChartData, registerables } from "chart.js";
import { CommonModule } from "@angular/common";

Chart.register(...registerables);

@Component({
  selector: "app-dashboard",
  standalone: true,
  imports: [CommonModule],
  templateUrl: "./dashboard.component.html",
  styleUrl: "./dashboard.component.scss",
})
export class DashboardComponent
  implements OnInit, AfterViewInit, OnDestroy, OnChanges
{
  @Input() totalLeads: number = 0;
  @Input() totalSessions: number = 0;
  @Input() totalDocuments: number = 0;
  @Input() todaySessions: number = 0;
  @Input() categorizationStats: any = {
    hot: 0,
    cold: 0,
    not_defined: 0,
    total: 0,
  };
  @Input() sessionTrends: any = {
    dates: [],
    session_counts: [],
    message_counts: [],
    avg_durations: []
  };
  @Input() enhancedMetrics: any = {
    avg_session_duration: 0,
    avg_messages_per_session: 0,
    total_messages: 0,
    active_sessions: 0,
    completed_sessions: 0,
    engagement_rate: 0,
    growth_rate: 0,
    peak_hours: [],
    return_visitor_rate: 0
  };

  @Output() tabChange = new EventEmitter<string>();
  @Output() exportLeads = new EventEmitter<void>();
  @Output() refreshAnalytics = new EventEmitter<void>();

  @ViewChild("categorizationChart", { static: false })
  chartCanvas!: ElementRef<HTMLCanvasElement>;

  @ViewChild('sessionTrendsChart', { static: false }) trendsChartCanvas!: ElementRef<HTMLCanvasElement>;

  // Chart instance
  private chart: Chart | null = null;
  private trendsChart: Chart | null = null;

  selectedTimeRange: 'week' | 'month' | 'quarter' = 'week';

  loadingTrends: boolean = false;
  loadingMetrics: boolean = false;

  ngOnInit(): void {
    console.log("🎯 DashboardComponent initialized");
  }

  ngAfterViewInit(): void {
    console.log("🎯 ngAfterViewInit called");
    console.log("🎯 Chart canvas element:", this.chartCanvas);
    console.log("🎯 Has categorization data:", this.hasCategorizationData());
    console.log("🎯 Categorization stats:", this.categorizationStats);
  
  }

  ngOnDestroy(): void {
    // Clean up chart instance
    if (this.chart) {
      this.chart.destroy();
    }
  }

  ngOnChanges(): void {
    console.log("🔄 Dashboard data changed:", this.categorizationStats);

    // Initialize chart when data changes AND we have data
    if (this.hasCategorizationData()) {
      setTimeout(() => {
        console.log("🎯 Data available, initializing chart...");
        this.initializeChart();
      }, 100);
    }
  }

 private initializeChart(): void {
  console.log('🎯 initializeChart called');
  
  if (!this.hasCategorizationData()) {
    console.error('❌ No categorization data available!');
    return;
  }

  // Wait a bit more for the DOM to update after *ngIf becomes true
  setTimeout(() => {
    if (!this.chartCanvas?.nativeElement) {
      console.error('❌ Chart canvas element not found!');
      return;
    }

    const ctx = this.chartCanvas.nativeElement.getContext('2d');
    if (!ctx) {
      console.error('❌ Failed to get canvas context!');
      return;
    }

    // Destroy existing chart if it exists
    if (this.chart) {
      this.chart.destroy();
    }

    try {
      // Create new chart
      this.chart = new Chart(ctx, {
        type: 'doughnut',
        data: this.getCategorizationChartData(),
        options: this.getChartOptions()
      });
      
      console.log('✅ Chart created successfully:', this.chart);
    } catch (error) {
      console.error('❌ Error creating chart:', error);
    }
  }, 50);
}

  onQuickAction(action: string): void {
    if (action === "leads") {
      this.tabChange.emit("leads");
    } else if (action === "sessions") {
      this.tabChange.emit("sessions");
    } else if (action === "export") {
      this.exportLeads.emit();
    }
  }

  getCategorizationChartData(): ChartData<"doughnut"> {
    // Get colors from CSS variables (computed at runtime)
    const rootStyles = getComputedStyle(document.documentElement);

    return {
      labels: ["Hot Leads", "Cold Leads", "Not Defined"],
      datasets: [
        {
          data: [
            this.categorizationStats.hot || 0,
            this.categorizationStats.cold || 0,
            this.categorizationStats.not_defined || 0,
          ],
          backgroundColor: [
            rootStyles.getPropertyValue("--lead-hot-color").trim() || "#ff4444",
            rootStyles.getPropertyValue("--lead-cold-color").trim() ||
              "#4169e1",
            rootStyles.getPropertyValue("--lead-undefined-color").trim() ||
              "#808080",
          ],
          borderWidth: 2,
          borderColor:
            rootStyles.getPropertyValue("--chart-border-color").trim() ||
            "#ffffff",
          hoverBorderWidth: 3,
          hoverOffset: 10,
        },
      ],
    };
  }

  getChartOptions(): ChartConfiguration<"doughnut">["options"] {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            padding: 20,
            usePointStyle: true,
            font: {
              size: 12,
              family: "Inter, system-ui, sans-serif",
            },
          },
        },
        tooltip: {
          callbacks: {
            label: (context: any) => {
              const label = context.label || "";
              const value = context.parsed || 0;
              const total = this.categorizationStats.total || 1;
              const percentage = ((value / total) * 100).toFixed(1);
              return `${label}: ${value} (${percentage}%)`;
            },
          },
        },
      },
      cutout: "50%",
      animation: {
        animateRotate: true,
        animateScale: true,
        duration: 1000,
        easing: "easeOutCubic",
      },
    };
  }

  hasCategorizationData(): boolean {
    return this.categorizationStats.total > 0;
  }

  getCategorizationPercentages(): any {
    const total = this.categorizationStats.total || 1;
    return {
      hot: ((this.categorizationStats.hot / total) * 100).toFixed(1),
      cold: ((this.categorizationStats.cold / total) * 100).toFixed(1),
      not_defined: (
        (this.categorizationStats.not_defined / total) *
        100
      ).toFixed(1),
    };
  }
}
