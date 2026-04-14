import { Component, OnInit, HostListener, Inject } from "@angular/core";
import { CommonModule, DOCUMENT } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { AgenticChatService } from "../../services/agentic-chat.service";
import {
  UniversityThemeService,
  UniversityBranding,
} from "../../services/university-theme.service";

import { DynamicTitleService } from "../../services/dynamic-title.service";
import { MarkdownPipe } from "./markdown.pipe";
import { ActivatedRoute } from "@angular/router";
// ✅ ADD: Import environment for API URL
import { environment } from "../../../environments/environment";

interface Message {
  type: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  isStreaming: boolean;
}

enum ChatStage {
  INITIAL = "initial",
  GREETING = "greeting",
  COLLECTING_DETAILS = "collecting_details",
  CHATTING = "chatting",
  ENDED = "ended",
  SHOWING_HISTORY = "showing_history",
}

enum DisplayMode {
  STANDALONE = "standalone",
  WIDGET = "widget",
}

@Component({
  selector: "app-chatbot",
  standalone: true,
  imports: [CommonModule, FormsModule, MarkdownPipe],
  templateUrl: "./chatbot.component.html",
  styleUrls: ["./chatbot.component.scss"],
})
export class ChatbotComponent implements OnInit {
  messages: Message[] = [];
  currentMessage: string = "";
  currentStage: ChatStage = ChatStage.INITIAL;

  universityBranding: UniversityBranding | null = null;
  brandingLoaded: boolean = false;
  universityXId: string = "";

  leadName: string = "";
  leadEmail: string = "";
  leadCountry: string = "";
  leadMobile: string = "";
  leadId: string = "";

  sessionId: string = "";
  isExistingLead: boolean = false;
  chatSummaries: any = null;

  isLoading: boolean = false;
  isTyping: boolean = false;
  showEndButton: boolean = false;
  showChatHistory: boolean = false;
  isSessionInitialized: boolean = false;

  //NEW: Thinking indicator properties
  thinkingMessages: string[] = ['Thinking...', 'Searching...', 'Processing...'];
  currentThinkingIndex: number = 0;
  thinkingInterval: any = null;

  //  NEW: Dual-mode functionality
  displayMode: DisplayMode = DisplayMode.STANDALONE;
  isWidgetMode: boolean = false;
  isEmbedded: boolean = false;
  widgetConfig: any = {};
  parentOrigin: string = "";
  
  // Widget-specific properties
  isMinimized: boolean = false;
  showWidgetHeader: boolean = true;
  compactMode: boolean = false;

  constructor(
    private chatService: AgenticChatService,
    private route: ActivatedRoute,
    private themeService: UniversityThemeService,
    private dynamicTitle: DynamicTitleService,
    @Inject(DOCUMENT) private document: Document
  ) {}

  ngOnInit() {
    // ✨ NEW: Detect display mode first
    this.detectDisplayMode();
    
    this.route.params.subscribe((params) => {
      this.universityXId = params["xId"];
      console.log("🏛️ University X-ID from URL:", this.universityXId);

      this.loadUniversityBranding();
    });
    
    // Set title only in standalone mode
    if (!this.isWidgetMode) {
      this.dynamicTitle.updateTitleForUniversity(this.universityXId);
    }

    // Initialize chat functionality
    this.currentStage = ChatStage.INITIAL;
    this.updateEndButtonVisibility();
    
    // Setup widget communication if needed
    if (this.isWidgetMode) {
      this.setupWidgetCommunication();
      this.notifyParentReady();
    }
    
    console.log(`ChatBot initialized in ${this.displayMode} mode - waiting for first user message`);
  }

  private loadUniversityBranding() {
    console.log("🎨 Loading branding for:", this.universityXId);

    this.themeService.loadUniversityBranding(this.universityXId).subscribe({
      next: (branding) => {
        this.universityBranding = branding;
        this.brandingLoaded = true;
        console.log("✅ Branding loaded in component:", branding);
      },
      error: (error) => {
        console.error("❌ Failed to load branding:", error);
        this.brandingLoaded = true; // Still show UI with defaults
      },
    });
  }

  // Getter methods for template usage
  get universityName(): string {
    const name = this.universityBranding?.university.name;
    // ✅ WHITE-LABEL: Show generic text if no university name
    return name && name.trim() ? name : "University";
  }

  get universityLogo(): string {
    // ✅ FIXED: Handle uploaded logo URLs properly
    const logoUrl = this.universityBranding?.branding.logo_url;
    
    if (logoUrl && logoUrl.trim()) {
      // ✅ Handle both relative and absolute URLs
      if (logoUrl.startsWith('/uploads/')) {
        // ✅ FIXED: Remove /api from environment.apiUrl since uploads are served at root level
        const baseUrl = environment.apiUrl.replace('/api', ''); // Remove /api suffix to get base URL
        return `${baseUrl}${logoUrl}`;
      }
      return logoUrl;
    }
    
    // ✅ WHITE-LABEL: Return empty string instead of fallback logo
    return "";
  }

  get welcomeMessage(): string {
    const name = this.universityName;
    // ✅ WHITE-LABEL: Generic welcome message
    return name === "University" ? "Welcome!" : `Welcome to ${name}!`;
  }

  get assistantDescription(): string {
    const name = this.universityName;
    // ✅ WHITE-LABEL: Generic description
    return name === "University" 
      ? "I'm here to help you with information about programs, admissions, and facilities."
      : `I'm here to help you with information about our programs, admissions, and facilities.`;
  }

  get chatMessagesClass(): string {
    return this.messages.length === 0 && !this.isLoading
      ? "empty-state"
      : "has-messages";
  }

  get chatInputClass(): string {
    return this.messages.length === 0 ? "hidden" : "";
  }

  private updateEndButtonVisibility() {
    this.showEndButton = !!(
      this.sessionId &&
      this.leadId &&
      this.currentStage === ChatStage.CHATTING
    );
  }

  private addMessage(
    type: "user" | "assistant" | "system",
    content: string,
    isStreaming = false
  ) {
    this.messages.push({
      type,
      content,
      timestamp: new Date(),
      isStreaming,
    });
    setTimeout(() => this.scrollToBottom(), 100);

    // ✨ NEW: Notify parent in widget mode
    if (this.isWidgetMode) {
      this.notifyParentEvent('message-added', {
        messageType: type,
        content: content.substring(0, 100), // Truncate for privacy
        messageCount: this.messages.length
      });
    }
  }

  private scrollToBottom() {
    const chatContainer = document.getElementById("chat-container");
    if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  sendMessage() {
    if (!this.currentMessage.trim() || this.isLoading) return;

    const userMessage = this.currentMessage.trim();
    this.addMessage("user", userMessage);
    this.currentMessage = "";

    // ✨ NEW: Notify parent of user message in widget mode
    if (this.isWidgetMode) {
      this.notifyParentEvent('message-sent', {
        content: userMessage.substring(0, 100) // Truncate for privacy
      });
    }

    //  NEW: Start thinking indicator immediately
    this.startThinkingIndicator();

    if (!this.isSessionInitialized) {
      this.initializeSessionOnFirstMessage(userMessage);
    } else {
      this.isLoading = true;
      this.handleUserMessage(userMessage);
    }
  }

  private initializeSessionOnFirstMessage(userMessage: string) {
    this.isSessionInitialized = true;
    this.isLoading = true;
    this.isTyping = true;

    const sessionData = {
      university_x_id: this.universityXId, // ← NEW: Use X-ID from URL
      name: this.leadName,
      email: this.leadEmail,
      country: this.leadCountry,
      mobile: this.leadMobile,
    };

    console.log(
      "🚀 Initializing session with university X-ID:",
      this.universityXId
    );
    console.log("📋 Session data:", sessionData);

    this.chatService
      .startPublicEnhancedSession(
        this.leadName,
        this.leadEmail,
        this.leadCountry,
        this.leadMobile,
        this.universityXId // ← FIXED: Pass actual X-ID instead of hardcoded "csss"
      )
      .subscribe({
        next: (response: any) => {
          if (response.success && response.session_id) {
            this.sessionId = response.session_id;
            this.leadId = response.lead_id || "";
            this.currentStage = ChatStage.CHATTING;
            this.updateEndButtonVisibility();

          console.log('✅ Session created for university X-ID:', this.universityXId);
          console.log('📋 Session ID:', this.sessionId);

          }
          this.sendUserMessageToBackend(userMessage);
        },
        error: (error) => {
          console.error('❌ Session initialization failed for X-ID:', this.universityXId, error);
          this.sendUserMessageToBackend(userMessage);
        },
      });
  }

  private sendUserMessageToBackend(message: string) {
    this.isTyping = true;
    this.isLoading = true;

    this.chatService
      .sendPublicEnhancedMessage(this.sessionId, message, this.leadId)
      .subscribe({
        next: (response: any) => {
          if (response.success && response.response) {
            this.streamAssistantResponse(response.response!);
          } else {
            this.addMessage(
              "system",
              "Error getting response. Please try again."
            );
            this.isLoading = false;
            this.isTyping = false;
          }
        },
        error: () => {
          this.chatService
            .sendMessage(this.sessionId, message, this.leadId)
            .subscribe({
              next: (response: any) => {
                if (response.success && response.response) {
                  this.streamAssistantResponse(response.response!);
                } else {
                  this.addMessage(
                    "assistant",
                    "I encountered an error. Please try again."
                  );
                  this.isLoading = false;
                  this.isTyping = false;
                }
              },
              error: () => {
                this.addMessage(
                  "assistant",
                  "I encountered an error. Please try again."
                );
                this.isLoading = false;
                this.isTyping = false;
              },
            });
        },
      });
  }

  private streamAssistantResponse(fullText: string) {
    // NEW: Stop thinking indicator and remove it
    this.stopThinkingIndicator();

    const newMessage: Message = {
      type: "assistant",
      content: "",
      timestamp: new Date(),
      isStreaming: true,
    };

    this.messages.push(newMessage);
    this.scrollToBottom();

    let index = 0;
    const speed = 1;

    const typeChar = () => {
      if (index < fullText.length) {
        newMessage.content += fullText.charAt(index++);
        setTimeout(typeChar, speed);
        this.scrollToBottom();
      } else {
        newMessage.isStreaming = false;
        this.isTyping = false;
        this.isLoading = false;
      }
    };

    typeChar();
  }

  private handleUserMessage(message: string) {
    this.handleChatting(message);
  }

  private handleChatting(message: string) {
    this.sendUserMessageToBackend(message);
  }

  endSession() {
    if (!this.sessionId || !this.leadId) {
      this.addMessage("assistant", "No active session to end.");
      this.showEndButton = false;
      return;
    }

    this.isLoading = true;
    this.chatService.endSession(this.sessionId, this.leadId).subscribe({
      next: (response) => {
        if (response.success) {
          this.addMessage("assistant", "Thank you! Your session has ended.");
          this.currentStage = ChatStage.ENDED;
          this.showEndButton = false;
        } else {
          this.addMessage(
            "system",
            `Error ending session: ${response.error || "Unknown error"}`
          );
        }
        this.isLoading = false;
      },
      error: () => {
        this.addMessage(
          "system",
          "Server error occurred while ending session."
        );
        this.isLoading = false;
      },
    });
  }

  onKeyPress(event: KeyboardEvent) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  onLogoError(event: any) {
    console.warn("⚠️ University logo failed to load");
    // ✅ WHITE-LABEL: Hide image instead of showing fallback logo
    event.target.style.display = 'none';
  }

  get canSendMessage(): boolean {
    return (
      this.currentMessage.trim() !== "" &&
      !this.isLoading &&
      this.brandingLoaded && 
      this.currentStage !== ChatStage.ENDED
    );
  }

  get ChatStage() {
    return ChatStage;
  }

  get DisplayMode() {
    return DisplayMode;
  }

  // ✨ NEW: Widget mode detection and setup methods
  private detectDisplayMode(): void {
    // Check URL parameters for widget/embedded mode
    const urlParams = new URLSearchParams(window.location.search);
    this.isWidgetMode = urlParams.get('widget') === 'true';
    this.isEmbedded = urlParams.get('embedded') === 'true';
    
    // Check if running in iframe
    this.isEmbedded = this.isEmbedded || (window.self !== window.top);
    
    // If embedded or widget mode, set widget display mode
    if (this.isWidgetMode || this.isEmbedded) {
      this.displayMode = DisplayMode.WIDGET;
      this.isWidgetMode = true;
      this.compactMode = true;
      this.showWidgetHeader = !urlParams.get('hideHeader');
      
      // Get parent origin for secure communication
      if (window.parent && window.parent !== window) {
        this.parentOrigin = document.referrer || '*';
      }
      
      console.log('🔗 Widget mode detected', {
        isWidgetMode: this.isWidgetMode,
        isEmbedded: this.isEmbedded,
        parentOrigin: this.parentOrigin,
        compactMode: this.compactMode
      });
    } else {
      this.displayMode = DisplayMode.STANDALONE;
      console.log('🖥️ Standalone mode detected');
    }
  }

  private setupWidgetCommunication(): void {
    // Listen for messages from parent window
    window.addEventListener('message', (event) => {
      // Verify origin for security (you can make this more strict)
      if (this.parentOrigin !== '*' && event.origin !== this.parentOrigin) {
        return;
      }

      const data = event.data;
      console.log('📨 Widget received message:', data);

      switch (data.type) {
        case 'widget-close':
          this.handleWidgetClose();
          break;
        case 'widget-minimize':
          this.handleWidgetMinimize();
          break;
        case 'widget-maximize':
          this.handleWidgetMaximize();
          break;
        case 'widget-config':
          this.updateWidgetConfig(data.config);
          break;
        case 'widget-theme':
          this.updateWidgetTheme(data.theme);
          break;
      }
    });
  }

  private notifyParentReady(): void {
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({
        type: 'chat-ready',
        university: this.universityXId,
        timestamp: new Date().toISOString()
      }, this.parentOrigin);
      console.log('📡 Notified parent: chat ready');
    }
  }

  private notifyParentEvent(eventType: string, data: any = {}): void {
    if (window.parent && window.parent !== window && this.isWidgetMode) {
      window.parent.postMessage({
        type: eventType,
        university: this.universityXId,
        timestamp: new Date().toISOString(),
        ...data
      }, this.parentOrigin);
    }
  }

  public handleWidgetClose(): void {
    console.log('🔒 Widget close requested');
    this.notifyParentEvent('chat-close-requested');
    // Don't actually close here, let parent handle it
  }

  public handleWidgetMinimize(): void {
    console.log('📉 Widget minimize requested');
    this.isMinimized = true;
    this.notifyParentEvent('chat-minimized');
  }

  public handleWidgetMaximize(): void {
    console.log('📈 Widget maximize requested');
    this.isMinimized = false;
    this.notifyParentEvent('chat-maximized');
  }

  private updateWidgetConfig(config: any): void {
    console.log('⚙️ Widget config updated:', config);
    this.widgetConfig = { ...this.widgetConfig, ...config };
    
    // Apply configuration changes
    if (config.compactMode !== undefined) {
      this.compactMode = config.compactMode;
    }
    if (config.showHeader !== undefined) {
      this.showWidgetHeader = config.showHeader;
    }
  }

  private updateWidgetTheme(theme: any): void {
    console.log('🎨 Widget theme updated:', theme);
    // Apply theme changes - you can extend this based on your needs
    if (theme.primaryColor) {
      document.documentElement.style.setProperty('--primary-color', theme.primaryColor);
    }
  }



  getPlaceholderText(): string {
    if (!this.brandingLoaded) {
      return "Loading...";
    }

    const universityName = this.universityName;

    switch (this.currentStage) {
      case ChatStage.INITIAL:
        return "Type your message to start chatting...";
      case ChatStage.CHATTING:
        return `Ask me anything about ${universityName}...`; // ← Dynamic university name!
      case ChatStage.SHOWING_HISTORY:
        return 'Type "new" to start fresh or "more" for detailed history...';
      default:
        return `Ask me anything about ${universityName}...`; // ← Dynamic university name!
    }
  }

  // ✨ NEW: Thinking indicator methods
  private startThinkingIndicator(): void {
    this.currentThinkingIndex = 0;
    this.addMessage("assistant", this.thinkingMessages[this.currentThinkingIndex], false);

    this.thinkingInterval = setInterval(() => {
      this.currentThinkingIndex = (this.currentThinkingIndex + 1) % this.thinkingMessages.length;
      // Update the last message content
      if (this.messages.length > 0 && this.messages[this.messages.length - 1].type === 'assistant') {
        this.messages[this.messages.length - 1].content = this.thinkingMessages[this.currentThinkingIndex];
      }
    }, 2000); // Change message every 2 seconds
  }

  private stopThinkingIndicator(): void {
    if (this.thinkingInterval) {
      clearInterval(this.thinkingInterval);
      this.thinkingInterval = null;
    }
    // Remove the thinking indicator message
    if (this.messages.length > 0 && this.messages[this.messages.length - 1].type === 'assistant' &&
        this.thinkingMessages.includes(this.messages[this.messages.length - 1].content)) {
      this.messages.pop();
    }
  }
}
