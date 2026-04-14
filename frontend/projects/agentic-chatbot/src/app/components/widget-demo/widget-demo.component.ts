import { Component, OnInit, AfterViewInit, OnDestroy, Inject } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({
  selector: 'app-widget-demo',
  standalone: true,
  templateUrl: './widget-demo.component.html',
  styleUrls: ['./widget-demo.component.scss']
})
export class WidgetDemoComponent implements OnInit, AfterViewInit, OnDestroy {
  logCount = 0;
  iframeSafeUrl: SafeResourceUrl;

  constructor(
    @Inject(DOCUMENT) private document: Document,
    private sanitizer: DomSanitizer
  ) {
    this.iframeSafeUrl = this.sanitizer.bypassSecurityTrustResourceUrl(
      `${window.location.origin}/chat/XNR35QWNP?widget=true&embedded=true`
    );
  }

  ngOnInit(): void {
    console.log('Widget Demo component initialized');
  }

  ngAfterViewInit(): void {
    // Auto-run tests after view initialization
    setTimeout(() => {
      this.log('University website loaded with chat widget');
      this.testAngularServer();
      this.testWidgetAPI();
    }, 1000);

    // Check for widget button
    setTimeout(() => {
      const widgetButton = this.document.getElementById('university-chat-widget-button');
      if (widgetButton) {
        this.log('Widget button found in DOM', 'success');
      } else {
        this.log('Widget button not found in DOM', 'error');
      }
    }, 2000);

    // Listen for widget messages
    window.addEventListener('message', (event) => {
      this.log('Received message: ' + JSON.stringify(event.data));
      
      if (event.data.type === 'chat-ready') {
        this.log('Chat is ready in iframe!', 'success');
        this.updateStatus('urlStatus', 'success', 'Chat Interface Loaded');
      }
    });

    // Load original widget script
    this.loadWidgetScript();
  }

  loadWidgetScript(): void {
    this.log('Loading original widget script...');
    
    const script = this.document.createElement('script');
    script.src = './assets/widget/widget-loader.js';
    script.setAttribute('data-university', 'XNR35QWNP');
    script.setAttribute('data-position', 'bottom-right');
    script.type = 'text/javascript';
    
    script.onload = () => {
      this.log('Original widget script loaded successfully', 'success');
      setTimeout(() => {
        this.testWidgetAPI();
      }, 1000);
    };
    
    script.onerror = (error) => {
      this.log('Widget script failed to load: ' + error, 'error');
    };
    
    this.document.head.appendChild(script);
  }

  log(message: string, type: string = 'info'): void {
    this.logCount++;
    const timestamp = new Date().toLocaleTimeString();
    const logEl = this.document.getElementById('debugLog');
    if (logEl) {
      const prefix = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
      logEl.textContent += `[${timestamp}] ${prefix} ${message}\n`;
      logEl.scrollTop = logEl.scrollHeight;
    }
    console.log(`Widget Activity:`, message);
  }

  clearLog(): void {
    const logEl = this.document.getElementById('debugLog');
    if (logEl) {
      logEl.textContent = 'Activity log cleared.\n';
    }
    this.logCount = 0;
  }

  updateStatus(elementId: string, status: string, message: string): void {
    const el = this.document.getElementById(elementId);
    if (el) {
      el.className = `status ${status}`;
      el.textContent = `${status === 'success' ? '✅' : status === 'error' ? '❌' : '🟡'} ${message}`;
    }
  }

  async testAngularServer(): Promise<void> {
    this.log('Testing chatbot service...');
    try {
      const response = await fetch(window.location.origin + '/', { mode: 'no-cors' });
      this.updateStatus('angularStatus', 'success', 'Chatbot Service Running');
      this.log('Chatbot service is accessible', 'success');
      
      // Test specific route
      setTimeout(() => {
        this.testChatbotRoute();
      }, 1000);
      
    } catch (error: any) {
      this.updateStatus('angularStatus', 'error', 'Chatbot Service Not Running');
      this.log('Chatbot service not accessible: ' + error.message, 'error');
      this.log('Please ensure the Angular service is running', 'error');
    }
  }

  async testChatbotRoute(): Promise<void> {
    this.log('Testing chatbot route...');
    try {
      const response = await fetch(window.location.origin + '/chat/XNR35QWNP', { mode: 'no-cors' });
      this.updateStatus('urlStatus', 'success', 'Chat Route OK');
      this.log('Chatbot route is accessible', 'success');
    } catch (error: any) {
      this.updateStatus('urlStatus', 'error', 'Chat Route Failed');
      this.log('Chatbot route failed: ' + error.message, 'error');
    }
  }

  testWidgetAPI(): void {
    this.log('Testing widget API...');
    if ((window as any).UniversityChatWidget) {
      this.updateStatus('widgetStatus', 'success', 'Widget API Loaded');
      this.log('Widget API is available', 'success');
      this.log('Config: ' + JSON.stringify((window as any).UniversityChatWidget.config()));
      
      // Test widget methods
      try {
        (window as any).UniversityChatWidget.open();
        this.log('Widget open() method works');
        setTimeout(() => {
          (window as any).UniversityChatWidget.close();
          this.log('Widget close() method works');
        }, 2000);
      } catch (error: any) {
        this.log('Widget method error: ' + error.message, 'error');
      }
    } else {
      this.updateStatus('widgetStatus', 'error', 'Widget API Not Loaded');
      this.log('Widget API not available', 'error');
    }
  }

  testIframe(): void {
    this.log('Testing iframe loading...');
    const iframe = this.document.getElementById('directIframe') as HTMLIFrameElement;
    if (iframe) {
      iframe.onload = () => {
        this.log('Direct iframe loaded successfully', 'success');
      };
      iframe.onerror = () => {
        this.log('Direct iframe failed to load', 'error');
      };
      
      // Force reload
      iframe.src = iframe.src;
    }
  }

  getIframeSrc(): SafeResourceUrl {
    return this.iframeSafeUrl;
  }



  ngOnDestroy(): void {
    // Clean up any widgets when component is destroyed
    const existingWidgets = this.document.querySelectorAll('[id*="widget"], .uc-widget-button, #university-chat-widget-button');
    existingWidgets.forEach(widget => widget.remove());
    this.log('Cleaned up widgets on component destroy');
  }
}
