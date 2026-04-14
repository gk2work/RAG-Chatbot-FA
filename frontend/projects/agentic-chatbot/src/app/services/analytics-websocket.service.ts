import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import io from 'socket.io-client';

export interface RealTimeUpdate {
  type: 'new_lead' | 'new_session' | 'new_user' | 'session_ended' | 'analytics_update';
  data: any;
  timestamp: string;
  university_x_id?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AnalyticsWebSocketService {
  private socket: any;
  private connected = false;
  
  // Observables for real-time updates
  private analyticsUpdates$ = new BehaviorSubject<RealTimeUpdate | null>(null);
  private connectionStatus$ = new BehaviorSubject<boolean>(false);
  
  constructor() {
    this.initializeConnection();
  }

  /**
   * Initialize WebSocket connection
   */
  private initializeConnection() {
  try {
    // Initialize Socket.IO connection
    this.socket = io(environment.apiUrl, {
      transports: ['websocket', 'polling'],
      timeout: 5000,
      auth: {
        token: localStorage.getItem('authToken') // SuperAdmin authentication
      }
    });

    // Connection successful
    this.socket.on('connect', () => {
      console.log('📡 Analytics WebSocket connected:', this.socket.id);
      this.connected = true;
      this.connectionStatus$.next(true);
      
      // Join analytics room for SuperAdmin updates
      this.socket.emit('join_analytics_room', { 
        role: 'superadmin',
        token: localStorage.getItem('authToken')
      });
    });

    // Connection failed
    this.socket.on('disconnect', () => {
      console.log('📡 Analytics WebSocket disconnected');
      this.connected = false;
      this.connectionStatus$.next(false);
    });

    // Listen for analytics updates
    this.socket.on('analytics_update', (update: RealTimeUpdate) => {
      console.log('📊 Real-time analytics update received:', update);
      this.analyticsUpdates$.next(update);
    });

  } catch (error) {
    console.error('❌ Failed to initialize WebSocket:', error);
  }
}

  /**
   * Get real-time analytics updates observable
   */
  getAnalyticsUpdates(): Observable<RealTimeUpdate | null> {
    return this.analyticsUpdates$.asObservable();
  }

  /**
   * Get connection status observable
   */
  getConnectionStatus(): Observable<boolean> {
    return this.connectionStatus$.asObservable();
  }
}