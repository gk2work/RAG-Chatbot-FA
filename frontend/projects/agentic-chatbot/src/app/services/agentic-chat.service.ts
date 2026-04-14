import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';

interface Lead {
  _id: string;
  name: string;
  email: string;
  university_code: string;
  created_at: string;
  status: string;
}

interface ChatMessage {
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface ChatResponse {
  success?: boolean;
  response?: string;
  error?: string;
  session_id?: string;
  chat_stored?: boolean;
  metadata?: any;
  contains_question?: boolean;
  conversation_aware?: boolean;
}

interface LiveChatSummary {
  session_id: string;
  user_message: string;
  assistant_response: string;
  timestamp: string;
  metadata: any;
}

interface SessionSummary {
  session_id: string;
  summary: any;
  created_at: string;
}

interface ChatSummaries {
  session_summaries: SessionSummary[];
  live_chat_summaries: LiveChatSummary[];
  total_sessions: number;
  total_live_chats: number;
}

interface LeadResponse {
  success: boolean;
  lead_id?: string;
  error?: string;
  message?: string;
  is_existing_lead?: boolean;
  chat_summaries?: ChatSummaries;
}

interface ChatSessionResponse {
  success?: boolean;
  session_id?: string;
  lead_id?: string;
  lead_name?: string;
  welcome_message?: string;
  error?: string;
  is_existing_lead?: boolean;
  conversation_memory_enabled?: boolean;
  dynamic_questioning_enabled?: boolean;
  university?: string;
  university_code?: string;
  university_x_id?: string;
}

interface ChatSummariesResponse {
  success: boolean;
  chat_summaries?: ChatSummaries;
  error?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AgenticChatService {
  // ✅ FIXED: environment.apiUrl already includes /api, so don't add it again
  private apiUrl = `${environment.apiUrl}/lead`;
  private chatApiUrl = `${environment.apiUrl}/chat`;

  constructor(private http: HttpClient) { }

  // Create a new lead or get existing lead with chat summaries
  createLead(name: string, email: string, country: string, mobile?: string, universityCode?:string): Observable<LeadResponse> {
    const payload: any = {
      name,
      email,
      country,
      university_code: universityCode
    };
    
    if (mobile) {
      payload.mobile = mobile;
    }
    
    return this.http.post<LeadResponse>(`${this.apiUrl}/create`, payload);
  }

  // Get chat summaries for a specific lead
  getChatSummaries(leadId: string): Observable<ChatSummariesResponse> {
    return this.http.get<ChatSummariesResponse>(`${this.apiUrl}/get-chat-summaries/${leadId}`);
  }

  // Start agentic chat session
  startAgenticChat(leadId: string, universityCode?: string): Observable<ChatSessionResponse> {
    return this.http.post<ChatSessionResponse>(`${this.apiUrl}/start-agentic-chat`, {
      lead_id: leadId,
      university_code: universityCode
    });
  }

  // Send chat message
  sendMessage(sessionId: string, message: string, leadId: string): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.apiUrl}/chat`, {
      session_id: sessionId,
      message,
      lead_id: leadId
    });
  }

  // Send enhanced chat message with conversational memory
  sendEnhancedMessage(sessionId: string, message: string, leadId: string): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.chatApiUrl}/message`, {
      session_id: sessionId,
      message,
      lead_id: leadId
    });
  }

  // End chat session
  endSession(sessionId: string, leadId: string): Observable<any> {
    const url = `${this.apiUrl}/end-session`;
    const payload = {
      session_id: sessionId,
      lead_id: leadId
    };
    
    console.log('🔗 AgenticChatService.endSession called');
    console.log('URL:', url);
    console.log('Payload:', payload);
    
    return this.http.post(url, payload).pipe(
      tap(response => {
        console.log('🎯 Service received response:', response);
      }),
      catchError(error => {
        console.error('🚨 Service error:', error);
        throw error;
      })
    );
  }

  // Get lead information
  getLead(leadId: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/get-lead/${leadId}`);
  }

  // Get all leads
  getAllLeads(): Observable<any> {
    return this.http.get(`${this.apiUrl}/get-leads`);
  }

  // Start enhanced public session with conversational memory (no authentication required)
  startPublicEnhancedSession(name?: string, email?: string, country?: string, mobile?: string, universityXId?: string): Observable<ChatSessionResponse> {
    const payload: any = {};
    
    // Send university X-ID if provided, otherwise fall back to default
    if (universityXId) {
      payload.university_x_id = universityXId;
    } else {
      payload.university_code = 'csss'; // Fallback to default university
    }
    
    // Add lead info if provided
    if (name) payload.name = name;
    if (email) payload.email = email;
    if (country) payload.country = country;
    if (mobile) payload.mobile = mobile;
    
    return this.http.post<ChatSessionResponse>(`${this.chatApiUrl}/start-public-session`, payload);
  }

  // Send enhanced chat message with conversational memory (public)
  sendPublicEnhancedMessage(sessionId: string, message: string, leadId?: string): Observable<ChatResponse> {
    const payload: any = {
      session_id: sessionId,
      message
    };
    
    if (leadId) {
      payload.lead_id = leadId;
    }
    
    return this.http.post<ChatResponse>(`${this.chatApiUrl}/public-message`, payload);
  }
}