import { Routes } from '@angular/router';
import { ChatbotComponent } from './components/chatbot/chatbot.component';
import { AdminPortalComponent } from './components/admin-portal/admin-portal.component';
import { SuperAdminComponent } from './components/super-admin/super-admin.component';
import { WidgetDemoComponent } from './components/widget-demo/widget-demo.component';
// Remove this import - we don't need it anymore
// import { SuperAdminLoginComponent } from './components/super-admin/login/super-admin-login.component';
import { UnifiedLoginComponent } from './components/auth/login/unified-login.component';
// Welcome component removed - direct to chatbot

export const routes: Routes = [
  { path: '', redirectTo: '/chat/XNR35QWNP', pathMatch: 'full' },
  { path: 'welcome/:xId', redirectTo: '/chat/:xId', pathMatch: 'full' },
  { path: 'welcome', redirectTo: '/chat/XNR35QWNP', pathMatch: 'full' },

  { path: 'chat/:xId', component: ChatbotComponent },
  { path: 'chat', redirectTo: '/chat/XNR35QWNP', pathMatch: 'full' },
  
  // Widget Demo/Test Page
  { path: 'widget-demo', component: WidgetDemoComponent },
  { path: 'demo', redirectTo: '/widget-demo', pathMatch: 'full' },
  
  // Unified Authentication
  { path: 'auth/login', component: UnifiedLoginComponent },
  
  // Admin Portal routes
  { path: 'admin', redirectTo: '/admin/dashboard', pathMatch: 'full' },
  { path: 'admin/dashboard', component: AdminPortalComponent, data: { activeTab: 'dashboard' } },
  { path: 'admin/leads', component: AdminPortalComponent, data: { activeTab: 'leads' } },
  { path: 'admin/sessions', component: AdminPortalComponent, data: { activeTab: 'sessions' } },
  { path: 'admin/universities', component: AdminPortalComponent, data: { activeTab: 'universities' } },

  // SuperAdmin routes - FIXED
  { path: 'superadmin/dashboard', component: SuperAdminComponent, data: { activeTab: 'dashboard' } },
  { path: 'superadmin/universities', component: SuperAdminComponent, data: { activeTab: 'universities' } },
  { path: 'superadmin/users', component: SuperAdminComponent, data: { activeTab: 'users' } },
  { path: 'superadmin/analytics', component: SuperAdminComponent, data: { activeTab: 'analytics' } },
  
  // SuperAdmin redirects
  { path: 'superadmin/login', redirectTo: '/auth/login', pathMatch: 'full' },  
  { path: 'superadmin', redirectTo: '/superadmin/dashboard', pathMatch: 'full' }, 
  
  { path: '**', redirectTo: '/chat/XNR35QWNP' }  
];