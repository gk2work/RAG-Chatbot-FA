# University Chatbot Widget Integration Guide
## ForeignAdmits Platform Integration

### 📋 Overview

This guide provides step-by-step instructions for integrating the University Chatbot Widget into the [ForeignAdmits platform](https://www.foreignadmits.com/). The widget enables university-specific AI chatbots that can assist students with admissions, programs, and university-related queries.

### 🎯 Integration Goals

- **Seamless Integration**: Embed university chatbots into ForeignAdmits without disrupting existing functionality
- **Multi-University Support**: Each university partner gets their own branded chatbot using unique X-IDs
- **Responsive Design**: Works across desktop, tablet, and mobile devices
- **Performance Optimized**: Minimal impact on page load times
- **Easy Configuration**: Simple setup for each university partner

---

## 🛠️ Technical Prerequisites

### Backend Requirements
- **University Chatbot API**: Running on designated server
- **University Database**: Configured with X-IDs for each university partner
- **CORS Configuration**: Allows requests from ForeignAdmits domains

### Frontend Requirements
- **Modern Browser Support**: ES6+ JavaScript compatibility
- **HTTPS**: Required for secure iframe communication
- **No Framework Dependencies**: Widget works with vanilla JavaScript

---

## 📦 Widget Files Structure

```
/chatbot-widget/
├── widget-loader.js          # Main widget SDK (production ready)
├── widget-loader.min.js      # Minified version
├── README.md                 # Basic documentation
├── INTEGRATION_GUIDE.md      # This file
└── examples/
    ├── basic-integration.html
    ├── react-integration.jsx
    └── vue-integration.vue
```

---

## 🚀 Quick Start Integration

### Method 1: Basic Script Tag (Recommended)

Add this single line to any page where you want the chatbot:

```html
<!-- Basic Integration -->
<script src="https://cdn.foreignadmits.com/chatbot/widget-loader.js" 
        data-university="UNIVERSITY_XID" 
        data-position="bottom-right"
        data-size="medium">
</script>
```

### Method 2: Programmatic Integration

```html
<script src="https://cdn.foreignadmits.com/chatbot/widget-loader.js"></script>
<script>
// Initialize after page load
document.addEventListener('DOMContentLoaded', function() {
    UniversityChatWidget.init({
        university: 'UNIVERSITY_XID',
        position: 'bottom-right',
        size: 'medium',
        theme: '#1976d2',
        showOnLoad: true
    });
});
</script>
```

---

## 🏛️ University Configuration

### Step 1: Obtain University X-ID

Each university partner in the ForeignAdmits network needs a unique X-ID:

```javascript
// Example X-IDs for different universities
const universityXIDs = {
    'harvard': 'XHR45VNWQ',
    'stanford': 'XST89BXPL', 
    'cambridge': 'XCB23MXRT',
    'oxford': 'XOX67KQWE',
    'mit': 'XMT12POIU'
};
```

### Step 2: Configure University in Backend

```bash
# Add university to database
curl -X POST https://api.foreignadmits.com/universities \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Harvard University",
    "code": "harvard",
    "x_id": "XHR45VNWQ",
    "branding": {
      "logo_url": "https://harvard.edu/logo.png",
      "primary_color": "#A51C30",
      "secondary_color": "#8B0000"
    }
  }'
```

---

## 🎨 ForeignAdmits-Specific Configuration

### Integration Points

Based on the [ForeignAdmits platform structure](https://www.foreignadmits.com/), here are recommended integration points:

#### 1. University Partner Pages
```html
<!-- On individual university pages -->
<!-- Example: /universities/harvard -->
<script>
// Get university X-ID from URL or database
const universityXID = getUniversityXIDFromPage(); // Your implementation
UniversityChatWidget.init({
    university: universityXID,
    position: 'bottom-right',
    size: 'large',
    customText: 'Chat with University',
    theme: '#1976d2' // ForeignAdmits brand color
});
</script>
```

#### 2. Student Dashboard
```html
<!-- In student portal -->
<script>
UniversityChatWidget.init({
    university: student.interestedUniversity.xId,
    position: 'bottom-left', // Different position to avoid conflicts
    size: 'medium',
    customText: 'Ask University'
});
</script>
```

#### 3. Consultant Portal
```html
<!-- For consultants helping students -->
<script>
// Multiple university support
const activeUniversities = getStudentUniversities(); // Your function
if (activeUniversities.length === 1) {
    UniversityChatWidget.init({
        university: activeUniversities[0].xId,
        customText: 'University Chat'
    });
}
</script>
```

---

## ⚙️ Configuration Options

### Complete Configuration Object

```javascript
UniversityChatWidget.init({
    // Required
    university: 'XHR45VNWQ',              // University X-ID (required)
    
    // Positioning
    position: 'bottom-right',             // bottom-right, bottom-left, top-right, top-left
    size: 'medium',                       // small, medium, large
    
    // Styling
    theme: '#1976d2',                     // Primary color (ForeignAdmits blue)
    customText: 'Chat with Harvard',      // Button text
    customIcon: '/icons/chat.svg',        // Custom icon URL
    borderRadius: '50px',                 // Button border radius
    
    // Behavior
    showOnLoad: true,                     // Show immediately
    pulseAnimation: true,                 // Enable pulse effect
    soundEnabled: false,                  // Notification sounds
    
    // Advanced
    apiUrl: 'https://api.foreignadmits.com', // Backend API
    chatUrl: 'https://chat.foreignadmits.com', // Chat interface
    zIndex: 999999,                       // CSS z-index
    
    // Analytics
    enableAnalytics: true,                // Track widget usage
    analyticsCallback: function(event) {  // Custom analytics
        // Send to ForeignAdmits analytics
        fa_analytics.track('chatbot_' + event.type, event.data);
    }
});
```

### Data Attributes Reference

```html
<script src="widget-loader.js"
        data-university="XHR45VNWQ"
        data-position="bottom-right"
        data-size="medium"
        data-theme="#1976d2"
        data-text="Chat with University"
        data-icon="/icons/chat.svg"
        data-show-on-load="true"
        data-pulse="true"
        data-sound="false">
</script>
```

---

## 🔗 ForeignAdmits Platform Integration

### 1. Dynamic University Detection

```javascript
// Example: Auto-detect university from current page
function getUniversityFromPage() {
    // Method 1: From URL
    const urlMatch = window.location.pathname.match(/\/universities\/([^\/]+)/);
    if (urlMatch) {
        return getXIDBySlug(urlMatch[1]);
    }
    
    // Method 2: From page data
    const universityData = document.querySelector('[data-university]');
    if (universityData) {
        return universityData.dataset.university;
    }
    
    // Method 3: From ForeignAdmits API
    return getCurrentUserUniversity();
}

// Initialize widget with detected university
const universityXID = getUniversityFromPage();
if (universityXID) {
    UniversityChatWidget.init({
        university: universityXID,
        theme: '#1976d2' // ForeignAdmits brand color
    });
}
```

### 2. User Context Integration

```javascript
// Pass user context to enhance chat experience
UniversityChatWidget.init({
    university: 'XHR45VNWQ',
    userContext: {
        studentId: getCurrentStudent()?.id,
        consultantId: getCurrentConsultant()?.id,
        source: 'foreignadmits',
        referrer: document.referrer
    }
});
```

### 3. Multi-Language Support

```javascript
// Support for ForeignAdmits' international users
const userLanguage = getUserLanguage(); // Your function

UniversityChatWidget.init({
    university: 'XHR45VNWQ',
    language: userLanguage,
    customText: getLocalizedText('chat_with_university', userLanguage)
});
```

---

## 📱 Responsive Design

### Mobile Optimization

```css
/* Custom CSS for ForeignAdmits mobile */
@media (max-width: 768px) {
    .uc-widget-button {
        bottom: 80px !important; /* Avoid bottom navigation */
    }
    
    .uc-modal {
        height: calc(100vh - 60px) !important; /* Account for header */
        top: 60px !important;
    }
}
```

### Integration with ForeignAdmits Mobile App

```javascript
// Detect if running in mobile app webview
const isApp = window.ForeignAdmitsApp !== undefined;

UniversityChatWidget.init({
    university: 'XHR45VNWQ',
    position: isApp ? 'top-right' : 'bottom-right',
    size: isApp ? 'small' : 'medium'
});
```

---

## 🔐 Security Configuration

### CORS Setup

```javascript
// Backend CORS configuration
const allowedOrigins = [
    'https://www.foreignadmits.com',
    'https://app.foreignadmits.com',
    'https://partner.foreignadmits.com',
    'https://staging.foreignadmits.com'
];
```

### Content Security Policy

```html
<!-- Add to ForeignAdmits pages -->
<meta http-equiv="Content-Security-Policy" 
      content="frame-src https://chat.foreignadmits.com; 
               script-src 'self' https://cdn.foreignadmits.com;">
```

---

## 📊 Analytics Integration

### Google Analytics

```javascript
// Track widget events in ForeignAdmits GA
window.addEventListener('message', function(event) {
    if (event.data.type === 'widget_opened') {
        gtag('event', 'chatbot_opened', {
            event_category: 'University Engagement',
            university_id: event.data.university,
            page_location: window.location.href
        });
    }
});
```

### Custom Analytics

```javascript
// ForeignAdmits custom analytics
UniversityChatWidget.init({
    university: 'XHR45VNWQ',
    analyticsCallback: function(event) {
        // Send to ForeignAdmits analytics API
        fetch('/api/analytics/chatbot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                event_type: event.type,
                university_id: event.university,
                user_id: getCurrentUser()?.id,
                timestamp: new Date().toISOString(),
                page_url: window.location.href,
                metadata: event.data
            })
        });
    }
});
```

---

## 🎨 Branding Customization

### ForeignAdmits Brand Integration

```javascript
// Use ForeignAdmits brand colors and styling
UniversityChatWidget.init({
    university: 'XHR45VNWQ',
    theme: '#1976d2',           // ForeignAdmits primary blue
    secondaryColor: '#f5f5f5',  // Light background
    customCSS: `
        .uc-widget-button {
            font-family: 'Inter', sans-serif; /* ForeignAdmits font */
            box-shadow: 0 4px 20px rgba(25, 118, 210, 0.3);
        }
        .uc-modal-header {
            background: linear-gradient(135deg, #1976d2, #1565c0);
        }
    `
});
```

### University-Specific Branding

```javascript
// Fetch university branding from ForeignAdmits API
async function initializeChatbot(universityXID) {
    const branding = await fetch(`/api/universities/${universityXID}/branding`);
    const brandData = await branding.json();
    
    UniversityChatWidget.init({
        university: universityXID,
        theme: brandData.primaryColor,
        customIcon: brandData.logoUrl,
        customText: `Chat with ${brandData.name}`
    });
}
```

---

## 🚀 Deployment Guide

### Step 1: Upload Widget Files

```bash
# Upload to ForeignAdmits CDN
aws s3 cp widget-loader.js s3://foreignadmits-cdn/chatbot/widget-loader.js
aws s3 cp widget-loader.min.js s3://foreignadmits-cdn/chatbot/widget-loader.min.js

# Set proper cache headers
aws s3api put-object-acl --bucket foreignadmits-cdn --key chatbot/widget-loader.js --acl public-read
```

### Step 2: Update ForeignAdmits Templates

```php
<!-- In ForeignAdmits PHP templates -->
<?php if ($university_page): ?>
<script src="<?= CDN_URL ?>/chatbot/widget-loader.js" 
        data-university="<?= htmlspecialchars($university['x_id']) ?>" 
        data-position="bottom-right"
        data-theme="<?= htmlspecialchars($university['brand_color']) ?>">
</script>
<?php endif; ?>
```

### Step 3: React Component (for ForeignAdmits React pages)

```jsx
// components/UniversityChatWidget.jsx
import { useEffect } from 'react';

const UniversityChatWidget = ({ universityXID, position = 'bottom-right' }) => {
    useEffect(() => {
        if (!universityXID) return;
        
        const script = document.createElement('script');
        script.src = 'https://cdn.foreignadmits.com/chatbot/widget-loader.js';
        script.setAttribute('data-university', universityXID);
        script.setAttribute('data-position', position);
        script.setAttribute('data-theme', '#1976d2');
        
        document.body.appendChild(script);
        
        return () => {
            // Cleanup
            if (window.UniversityChatWidget) {
                window.UniversityChatWidget.hide();
            }
            document.body.removeChild(script);
        };
    }, [universityXID, position]);
    
    return null; // Widget renders itself
};

export default UniversityChatWidget;
```

### Step 4: Vue Component (for ForeignAdmits Vue pages)

```vue
<!-- components/UniversityChatWidget.vue -->
<template>
  <div></div> <!-- Widget renders itself -->
</template>

<script>
export default {
    name: 'UniversityChatWidget',
    props: {
        universityXID: {
            type: String,
            required: true
        },
        position: {
            type: String,
            default: 'bottom-right'
        }
    },
    mounted() {
        this.loadWidget();
    },
    beforeUnmount() {
        this.cleanupWidget();
    },
    methods: {
        loadWidget() {
            const script = document.createElement('script');
            script.src = 'https://cdn.foreignadmits.com/chatbot/widget-loader.js';
            script.setAttribute('data-university', this.universityXID);
            script.setAttribute('data-position', this.position);
            document.body.appendChild(script);
        },
        cleanupWidget() {
            if (window.UniversityChatWidget) {
                window.UniversityChatWidget.hide();
            }
        }
    }
};
</script>
```

---

## 🧪 Testing Guide

### Local Testing

```bash
# 1. Start the chatbot backend
cd university-chatbot-backend
python app.py

# 2. Start the chatbot frontend
cd university-chatbot-frontend
ng serve

# 3. Test widget on ForeignAdmits pages
# Open browser to: http://localhost:3000/test-page
```

### Test Checklist

- [ ] **Widget Loads**: Floating button appears
- [ ] **University Branding**: Correct logo and colors
- [ ] **Chat Functionality**: Can send/receive messages
- [ ] **Responsive**: Works on mobile devices
- [ ] **Multiple Universities**: Different X-IDs work correctly
- [ ] **Analytics**: Events are tracked properly
- [ ] **Performance**: No impact on page load speed

### Test Universities

```javascript
// Test with these sample universities
const testUniversities = [
    { xId: 'XHR45VNWQ', name: 'Harvard University' },
    { xId: 'XST89BXPL', name: 'Stanford University' },
    { xId: 'XMT12POIU', name: 'MIT' }
];
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Widget Not Loading

```javascript
// Debug widget loading
console.log('Widget API:', window.UniversityChatWidget);
console.log('Widget config:', window.UniversityChatWidget?.config());

// Check for script errors
window.addEventListener('error', function(e) {
    if (e.filename.includes('widget-loader')) {
        console.error('Widget script error:', e);
    }
});
```

#### 2. University Not Found

```javascript
// Validate X-ID format
function isValidXID(xId) {
    return /^X[A-Z0-9]{8}$/.test(xId);
}

// Check university exists
async function validateUniversity(xId) {
    const response = await fetch(`/api/universities/${xId}/validate`);
    return response.ok;
}
```

#### 3. CORS Issues

```javascript
// Check CORS configuration
fetch('https://chat.foreignadmits.com/health')
    .then(response => console.log('CORS OK'))
    .catch(error => console.error('CORS issue:', error));
```

### Debug Mode

```javascript
// Enable debug mode
UniversityChatWidget.init({
    university: 'XHR45VNWQ',
    debug: true, // Enables console logging
    debugLevel: 'verbose' // 'minimal', 'normal', 'verbose'
});
```

---

## 📈 Performance Optimization

### Lazy Loading

```javascript
// Load widget only when needed
function loadChatWidget(universityXID) {
    if (document.getElementById('chat-widget-loaded')) return;
    
    const script = document.createElement('script');
    script.id = 'chat-widget-loaded';
    script.src = 'https://cdn.foreignadmits.com/chatbot/widget-loader.js';
    script.onload = () => {
        UniversityChatWidget.init({
            university: universityXID,
            showOnLoad: false // Don't show immediately
        });
    };
    document.head.appendChild(script);
}

// Load when user scrolls or after delay
setTimeout(() => loadChatWidget('XHR45VNWQ'), 3000);
```

### CDN Configuration

```javascript
// Use CDN with proper caching
const CDN_CONFIG = {
    baseUrl: 'https://cdn.foreignadmits.com',
    version: 'v1.0.0',
    cache: '1d' // 1 day cache
};

const widgetUrl = `${CDN_CONFIG.baseUrl}/chatbot/${CDN_CONFIG.version}/widget-loader.js`;
```

---

## 📞 Support & Maintenance

### Monitoring

```javascript
// Monitor widget health
setInterval(() => {
    if (window.UniversityChatWidget) {
        const health = window.UniversityChatWidget.getHealth();
        if (!health.isHealthy) {
            // Alert monitoring system
            sendAlert('Widget health issue', health);
        }
    }
}, 60000); // Check every minute
```

### Updates

```bash
# Update widget version
./scripts/deploy-widget.sh v1.1.0

# Rollback if needed
./scripts/rollback-widget.sh v1.0.0
```

### Support Contacts

- **Technical Issues**: dev-team@foreignadmits.com
- **University Onboarding**: partnerships@foreignadmits.com
- **Widget Configuration**: chatbot-support@foreignadmits.com

---

## 🎯 Best Practices

### 1. Performance
- Load widget asynchronously
- Use CDN for static assets
- Implement lazy loading for non-critical pages

### 2. User Experience
- Position widget to avoid UI conflicts
- Use university-specific branding
- Test on multiple devices and browsers

### 3. Analytics
- Track widget usage and conversion
- Monitor chat completion rates
- Analyze user satisfaction

### 4. Security
- Validate all X-IDs server-side
- Use HTTPS for all communications
- Implement proper CORS policies

### 5. Maintenance
- Regular health checks
- Version control for widget updates
- Backup and rollback procedures

---

## 📚 Additional Resources

### Documentation
- [Widget API Reference](./API_REFERENCE.md)
- [University Onboarding Guide](./UNIVERSITY_ONBOARDING.md)
- [Troubleshooting FAQ](./TROUBLESHOOTING.md)

### Examples
- [Live Demo](https://demo.foreignadmits.com/chatbot)
- [Integration Examples](./examples/)
- [Test Universities](./test-data.json)

### Support
- [GitHub Issues](https://github.com/foreignadmits/chatbot-widget/issues)
- [Developer Forum](https://developers.foreignadmits.com/chatbot)
- [Status Page](https://status.foreignadmits.com)

---

*This integration guide is maintained by the ForeignAdmits Development Team. Last updated: December 2024*
