# University Chatbot Widget

A lightweight, embeddable chat widget that allows any website to integrate university-specific AI chatbot functionality with just a few lines of code.

## 🚀 Quick Start

### Basic Integration (Easiest)

Add this single line to your website:

```html
<script src="https://your-domain.com/widget/widget-loader.js" 
        data-university="csss" 
        data-position="bottom-right">
</script>
```

### Advanced Integration (More Control)

```html
<script src="https://your-domain.com/widget/widget-loader.js"></script>
<script>
UniversityChatWidget.init({
    university: 'csss',
    position: 'bottom-right',
    size: 'medium',
    theme: '#0c3c8c',
    showOnLoad: true
});
</script>
```

## 📋 Configuration Options

### Data Attributes (Basic Integration)

| Attribute | Default | Description |
|-----------|---------|-------------|
| `data-university` | `csss` | University identifier (required) |
| `data-position` | `bottom-right` | Widget position (`bottom-right`, `bottom-left`, `top-right`, `top-left`) |
| `data-size` | `medium` | Widget size (`small`, `medium`, `large`) |
| `data-theme` | `blue` | Color theme (`blue`, `green`, `purple`, or hex color) |
| `data-text` | `Chat with us` | Custom button text |
| `data-icon` | Default chat icon | Custom icon URL |
| `data-show-on-load` | `true` | Show widget immediately |
| `data-pulse` | `true` | Enable pulse animation |
| `data-sound` | `false` | Enable notification sounds |

### JavaScript API (Advanced Integration)

```javascript
UniversityChatWidget.init({
    // Required
    university: 'csss',              // University identifier
    
    // Positioning
    position: 'bottom-right',        // Widget position
    size: 'medium',                  // Widget size
    
    // Styling
    theme: '#0c3c8c',               // Primary color
    borderRadius: '50px',           // Button border radius
    boxShadow: '0 4px 16px rgba(0,0,0,0.2)', // Button shadow
    
    // Behavior
    showOnLoad: true,               // Show immediately
    pulseAnimation: true,           // Enable pulse effect
    soundEnabled: false,            // Enable sounds
    
    // Customization
    customText: 'Need help?',       // Button text
    customIcon: '/path/to/icon.svg', // Custom icon
    
    // Technical
    apiUrl: 'https://api.example.com', // Backend API URL
    chatUrl: 'https://chat.example.com', // Chat interface URL
    zIndex: 999999                  // CSS z-index
});
```

## 🎛️ API Methods

### Control Methods

```javascript
// Open/close chat
UniversityChatWidget.open();        // Open chat modal
UniversityChatWidget.close();       // Close chat modal
UniversityChatWidget.toggle();      // Toggle open/close

// Show/hide widget
UniversityChatWidget.show();        // Show widget button
UniversityChatWidget.hide();        // Hide widget button

// Get state
const isOpen = UniversityChatWidget.isOpen();     // Returns boolean
const config = UniversityChatWidget.config();     // Returns config object
```

### Event Handling

```javascript
// Listen for widget events
window.addEventListener('message', function(event) {
    const data = event.data;
    
    switch (data.type) {
        case 'widget_opened':
            console.log('Chat opened');
            break;
            
        case 'widget_closed':
            console.log('Chat closed');
            break;
            
        case 'message_sent':
            console.log('User sent message:', data.content);
            break;
            
        case 'message_received':
            console.log('Bot response received');
            break;
    }
});
```

## 🎨 Styling & Theming

### CSS Custom Properties

The widget uses CSS custom properties that can be overridden:

```css
:root {
    --uc-primary-color: #0c3c8c;
    --uc-secondary-color: #667eea;
    --uc-text-color: #ffffff;
    --uc-shadow: 0 4px 16px rgba(0,0,0,0.15);
    --uc-border-radius: 50px;
    --uc-z-index: 999999;
}
```

### University Branding

The widget automatically loads university-specific branding:

- **Logo**: University logo in chat header
- **Colors**: Primary and secondary brand colors
- **Name**: University name in interface
- **Custom messaging**: University-specific welcome messages

## 📱 Responsive Design

### Desktop (> 768px)
- Positioned modal overlay (400x600px)
- Floating button in specified corner
- Hover effects and animations

### Mobile (≤ 768px)
- Full-screen modal interface
- Slide-up animation from bottom
- Touch-optimized controls
- Native app-like experience

## 🔒 Security Features

### Iframe Sandboxing
- Secure iframe isolation
- Prevents code injection
- Limited permissions (`allow-scripts`, `allow-same-origin`, `allow-forms`)

### Cross-Domain Security
- CSP headers for content security
- Origin verification for messages
- HTTPS-only communication

### Data Protection
- No localStorage usage
- Session data in iframe only
- Secure cross-domain messaging

## ⚡ Performance

### Loading Strategy
- **Lazy Loading**: Chat interface loads only when opened
- **Minimal Footprint**: < 50KB JavaScript file
- **CDN Delivery**: Fast global loading
- **Smart Caching**: Optimized for repeat visits

### Optimization Features
- Compressed assets
- Tree-shaking for unused code
- Progressive enhancement
- Graceful degradation

## 🏛️ Multi-University Support

### University Configuration
Each university has its own configuration:

```javascript
// Automatically loads university-specific:
// - Branding (logo, colors, messaging)
// - AI training data
// - Custom features
// - Contact information

UniversityChatWidget.init({
    university: 'harvard',  // Loads Harvard branding
    // ... other options
});
```

### Switching Universities
```javascript
// Dynamic university switching (if implemented)
UniversityChatWidget.switchUniversity('mit');
```

## 🔧 Integration Examples

### WordPress Integration

```php
// In functions.php
function add_university_chat_widget() {
    $university_id = get_option('university_chat_id', 'csss');
    $position = get_option('university_chat_position', 'bottom-right');
    
    echo "<script src='https://your-domain.com/widget/widget-loader.js' 
                  data-university='{$university_id}' 
                  data-position='{$position}'>
          </script>";
}
add_action('wp_footer', 'add_university_chat_widget');
```

### React Integration

```jsx
import { useEffect } from 'react';

function ChatWidget({ university = 'csss' }) {
    useEffect(() => {
        // Load widget script
        const script = document.createElement('script');
        script.src = 'https://your-domain.com/widget/widget-loader.js';
        script.setAttribute('data-university', university);
        script.setAttribute('data-position', 'bottom-right');
        document.body.appendChild(script);
        
        return () => {
            // Cleanup on unmount
            document.body.removeChild(script);
        };
    }, [university]);
    
    return null;
}
```

### Vue.js Integration

```vue
<template>
  <div id="app">
    <!-- Your app content -->
  </div>
</template>

<script>
export default {
    mounted() {
        window.UniversityChatWidget.init({
            university: this.universityId,
            position: 'bottom-right',
            size: 'medium'
        });
    },
    data() {
        return {
            universityId: 'csss'
        };
    }
};
</script>
```

## 📊 Analytics & Tracking

### Built-in Analytics
```javascript
// Automatic event tracking
UniversityChatWidget.init({
    university: 'csss',
    analytics: true,  // Enable built-in analytics
    analyticsEndpoint: 'https://analytics.example.com/track'
});
```

### Google Analytics Integration
```javascript
// Automatically sends events to Google Analytics if available
// Event categories: 'University Chat Widget'
// Event actions: 'opened', 'closed', 'message_sent', etc.
```

### Custom Analytics
```javascript
window.addEventListener('message', function(event) {
    if (event.data.type === 'widget_opened') {
        // Send to your analytics service
        analytics.track('Chat Widget Opened', {
            university: event.data.university,
            page: window.location.pathname
        });
    }
});
```

## 🐛 Troubleshooting

### Common Issues

**Widget not showing:**
```javascript
// Check if script loaded
console.log(window.UniversityChatWidget); // Should be defined

// Check console for errors
// Verify university ID is correct
// Check network requests in DevTools
```

**Styling conflicts:**
```css
/* Increase specificity if needed */
.uc-widget-button {
    all: initial !important;
    /* Reset all inherited styles */
}
```

**Mobile issues:**
```javascript
// Check viewport meta tag
<meta name="viewport" content="width=device-width, initial-scale=1.0">

// Test on actual devices, not just browser dev tools
```

### Debug Mode
```javascript
UniversityChatWidget.init({
    university: 'csss',
    debug: true  // Enable console logging
});
```

## 🔄 Updates & Versioning

### Auto-Updates
The widget automatically updates when new versions are deployed to the CDN.

### Version Pinning
```html
<!-- Pin to specific version if needed -->
<script src="https://your-domain.com/widget/v1.2.3/widget-loader.js"></script>
```

### Breaking Changes
Major version updates may include breaking changes. Check the changelog before updating.

## 📞 Support

### Documentation
- [Integration Guide](./docs/integration.md)
- [API Reference](./docs/api.md)
- [Customization Guide](./docs/customization.md)

### Getting Help
- 📧 Email: support@university-chatbot.com
- 💬 Live Chat: Use the widget on our website!
- 📖 Documentation: [docs.university-chatbot.com](https://docs.university-chatbot.com)
- 🐛 Issues: [GitHub Issues](https://github.com/university-chatbot/widget/issues)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

*Made with ❤️ for universities worldwide*
