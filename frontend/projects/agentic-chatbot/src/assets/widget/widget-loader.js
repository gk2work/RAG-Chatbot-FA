/**
 * University Chatbot Widget Loader
 * Embeddable widget for integrating university chatbot into any website
 * 
 * Usage:
 * <script src="path/to/widget-loader.js" 
 *         data-university="csss" 
 *         data-position="bottom-right"
 *         data-theme="blue">
 * </script>
 */

(function() {
    'use strict';

    // Prevent multiple widget instances
    if (window.UniversityChatWidget) {
        return;
    }

    // Default configuration
    const DEFAULT_CONFIG = {
        position: 'bottom-right', // bottom-right, bottom-left, top-right, top-left
        theme: 'blue',
        size: 'medium', // small, medium, large
        university: 'XNR35QWNP',
        apiUrl: 'https://dev-uni-chat-be.foreignadmits.app', // Will be replaced with production URL
        chatUrl: 'https://dev-uni-chat.foreignadmits.app', // Will be replaced with production URL
        zIndex: 999999,
        showOnLoad: true,
        customText: null,
        customIcon: null,
        borderRadius: '50px',
        boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
        pulseAnimation: true,
        soundEnabled: false
    };

    // Widget state
    let isOpen = false;
    let config = {};
    let widgetButton = null;
    let chatModal = null;
    let chatIframe = null;
    let overlay = null;

    /**
     * Initialize the widget
     */
    function init(customConfig = {}) {
        try {
            // Merge configuration
            config = { ...DEFAULT_CONFIG, ...getScriptConfig(), ...customConfig };
            
            // Validate required parameters
            if (!config.university) {
                console.error('University Chatbot Widget: university parameter is required');
                return;
            }

            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', createWidget);
            } else {
                createWidget();
            }

            // Load university configuration
            loadUniversityConfig();

        } catch (error) {
            console.error('University Chatbot Widget initialization failed:', error);
        }
    }

    /**
     * Get configuration from script tag attributes
     */
    function getScriptConfig() {
        const script = document.currentScript || 
                      document.querySelector('script[src*="widget-loader"]') ||
                      document.querySelector('script[data-university]');
        
        if (!script) return {};

        return {
            university: script.getAttribute('data-university') || DEFAULT_CONFIG.university,
            position: script.getAttribute('data-position') || DEFAULT_CONFIG.position,
            theme: script.getAttribute('data-theme') || DEFAULT_CONFIG.theme,
            size: script.getAttribute('data-size') || DEFAULT_CONFIG.size,
            apiUrl: script.getAttribute('data-api-url') || DEFAULT_CONFIG.apiUrl,
            chatUrl: script.getAttribute('data-chat-url') || DEFAULT_CONFIG.chatUrl,
            customText: script.getAttribute('data-text'),
            customIcon: script.getAttribute('data-icon'),
            showOnLoad: script.getAttribute('data-show-on-load') !== 'false',
            pulseAnimation: script.getAttribute('data-pulse') !== 'false',
            soundEnabled: script.getAttribute('data-sound') === 'true'
        };
    }

    /**
     * Load university-specific configuration
     */
    async function loadUniversityConfig() {
        try {
            const response = await fetch(`${config.apiUrl}/api/universities/${config.university}/branding`);
            if (response.ok) {
                const brandingData = await response.json();
                if (brandingData.success && brandingData.branding) {
                    // Update config with university branding
                    config.universityName = brandingData.university?.name || 'University';
                    config.universityLogo = brandingData.branding?.logo_url;
                    config.primaryColor = brandingData.branding?.primary_color || '#0c3c8c';
                    config.secondaryColor = brandingData.branding?.secondary_color || '#667eea';
                    
                    // Update widget appearance with university branding
                    updateWidgetBranding();
                }
            }
        } catch (error) {
            console.warn('Could not load university branding:', error);
        }
    }

    /**
     * Create the widget elements
     */
    function createWidget() {
        createWidgetButton();
        createChatModal();
        injectStyles();
        
        if (config.showOnLoad) {
            showWidget();
        }
    }

    /**
     * Create the floating chat button
     */
    function createWidgetButton() {
        widgetButton = document.createElement('div');
        widgetButton.id = 'university-chat-widget-button';
        widgetButton.className = `uc-widget-button uc-position-${config.position} uc-size-${config.size}`;
        
        const buttonContent = `
            <div class="uc-button-content">
                <div class="uc-icon-container">
                    ${getButtonIcon()}
                </div>
                <div class="uc-button-text">${getButtonText()}</div>
                ${config.pulseAnimation ? '<div class="uc-pulse-ring"></div>' : ''}
            </div>
        `;
        
        widgetButton.innerHTML = buttonContent;
        widgetButton.addEventListener('click', toggleChat);
        
        // Add hover effects
        widgetButton.addEventListener('mouseenter', handleButtonHover);
        widgetButton.addEventListener('mouseleave', handleButtonLeave);
        
        document.body.appendChild(widgetButton);
    }

    /**
     * Create the chat modal container
     */
    function createChatModal() {
        // Create overlay
        overlay = document.createElement('div');
        overlay.id = 'university-chat-widget-overlay';
        overlay.className = 'uc-overlay';
        overlay.addEventListener('click', closeChat);
        
        // Create modal
        chatModal = document.createElement('div');
        chatModal.id = 'university-chat-widget-modal';
        chatModal.className = `uc-modal uc-position-${config.position}`;
        
        const modalContent = `
            <div class="uc-modal-header">
                <div class="uc-header-info">
                    <div class="uc-university-logo">
                        ${config.universityLogo ? `<img src="${getFullLogoUrl()}" alt="${config.universityName} Logo" />` : ''}
                    </div>
                    <div class="uc-header-text">
                        <h3>${config.universityName || 'University'}</h3>
                        <p>AI Assistant</p>
                    </div>
                </div>
                <button class="uc-close-button" aria-label="Close chat">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
            <div class="uc-modal-body">
                <div class="uc-loading-placeholder">
                    <div class="uc-loading-spinner"></div>
                    <p>Loading chat...</p>
                </div>
            </div>
        `;
        
        chatModal.innerHTML = modalContent;
        
        // Add close button functionality
        const closeButton = chatModal.querySelector('.uc-close-button');
        closeButton.addEventListener('click', closeChat);
        
        document.body.appendChild(overlay);
        document.body.appendChild(chatModal);
    }

    /**
     * Create and load the chat iframe
     */
    function createChatIframe() {
        if (chatIframe) return; // Already created
        
        chatIframe = document.createElement('iframe');
        chatIframe.id = 'university-chat-widget-iframe';
        chatIframe.className = 'uc-iframe';
        chatIframe.src = `${config.chatUrl}/chat/${config.university}?widget=true&embedded=true&hideHeader=false`;
        chatIframe.frameBorder = '0';
        chatIframe.allow = 'microphone; camera; encrypted-media; autoplay';
        chatIframe.sandbox = 'allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-top-navigation';
        
        // Replace loading placeholder with iframe
        const modalBody = chatModal.querySelector('.uc-modal-body');
        const loadingPlaceholder = modalBody.querySelector('.uc-loading-placeholder');
        
        chatIframe.onload = function() {
            loadingPlaceholder.style.display = 'none';
            chatIframe.style.display = 'block';
            
            // Setup iframe communication
            setupIframeMessaging();
        };
        
        modalBody.appendChild(chatIframe);
    }

    /**
     * Setup communication with iframe
     */
    function setupIframeMessaging() {
        window.addEventListener('message', function(event) {
            // Verify origin for security
            if (!event.origin.includes(new URL(config.chatUrl).hostname)) {
                return;
            }
            
            const data = event.data;
            
            switch (data.type) {
                case 'chat-resize':
                    resizeModal(data.height);
                    break;
                case 'chat-close':
                    closeChat();
                    break;
                case 'chat-minimize':
                    minimizeChat();
                    break;
                case 'chat-ready':
                    onChatReady();
                    break;
                case 'new-message':
                    handleNewMessage(data.content);
                    break;
            }
        });
    }

    /**
     * Toggle chat open/close
     */
    function toggleChat() {
        if (isOpen) {
            closeChat();
        } else {
            openChat();
        }
    }

    /**
     * Open chat modal
     */
    function openChat() {
        if (isOpen) return;
        
        isOpen = true;
        
        // Create iframe if not exists
        if (!chatIframe) {
            createChatIframe();
        }
        
        // Show modal with animation
        overlay.classList.add('uc-show');
        chatModal.classList.add('uc-show');
        widgetButton.classList.add('uc-chat-open');
        
        // Update button icon
        updateButtonIcon('close');
        
        // Prevent body scroll on mobile
        document.body.style.overflow = 'hidden';
        
        // Focus management for accessibility
        trapFocus();
        
        // Analytics
        trackEvent('widget_opened');
    }

    /**
     * Close chat modal
     */
    function closeChat() {
        if (!isOpen) return;
        
        isOpen = false;
        
        // Hide modal with animation
        overlay.classList.remove('uc-show');
        chatModal.classList.remove('uc-show');
        widgetButton.classList.remove('uc-chat-open');
        
        // Update button icon
        updateButtonIcon('chat');
        
        // Restore body scroll
        document.body.style.overflow = '';
        
        // Return focus to button
        widgetButton.focus();
        
        // Analytics
        trackEvent('widget_closed');
    }

    /**
     * Get button icon based on config and state
     */
    function getButtonIcon() {
        if (config.customIcon) {
            return `<img src="${config.customIcon}" alt="Chat" />`;
        }
        
        return `
            <svg class="uc-icon uc-icon-chat" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z"></path>
            </svg>
            <svg class="uc-icon uc-icon-close" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        `;
    }

    /**
     * Get button text
     */
    function getButtonText() {
        if (config.customText) {
            return config.customText;
        }
        
        return config.size === 'small' ? '' : 'Chat with us';
    }

    /**
     * Update button icon for different states
     */
    function updateButtonIcon(state) {
        const chatIcon = widgetButton.querySelector('.uc-icon-chat');
        const closeIcon = widgetButton.querySelector('.uc-icon-close');
        
        if (state === 'close') {
            if (chatIcon) chatIcon.style.display = 'none';
            if (closeIcon) closeIcon.style.display = 'block';
        } else {
            if (chatIcon) chatIcon.style.display = 'block';
            if (closeIcon) closeIcon.style.display = 'none';
        }
    }

    /**
     * Get full logo URL
     */
    function getFullLogoUrl() {
        if (!config.universityLogo) return '';
        
        if (config.universityLogo.startsWith('http')) {
            return config.universityLogo;
        }
        
        if (config.universityLogo.startsWith('/')) {
            const baseUrl = config.apiUrl.replace('/api', '');
            return `${baseUrl}${config.universityLogo}`;
        }
        
        return config.universityLogo;
    }

    /**
     * Update widget with university branding
     */
    function updateWidgetBranding() {
        if (widgetButton && config.primaryColor) {
            widgetButton.style.setProperty('--uc-primary-color', config.primaryColor);
            widgetButton.style.setProperty('--uc-secondary-color', config.secondaryColor || config.primaryColor);
        }
        
        if (chatModal) {
            // Update university name and logo in modal header
            const headerText = chatModal.querySelector('.uc-header-text h3');
            const logoContainer = chatModal.querySelector('.uc-university-logo');
            
            if (headerText) {
                headerText.textContent = config.universityName || 'University';
            }
            
            if (logoContainer && config.universityLogo) {
                logoContainer.innerHTML = `<img src="${getFullLogoUrl()}" alt="${config.universityName} Logo" />`;
            }
        }
    }

    /**
     * Handle button hover
     */
    function handleButtonHover() {
        widgetButton.classList.add('uc-hover');
    }

    /**
     * Handle button leave
     */
    function handleButtonLeave() {
        widgetButton.classList.remove('uc-hover');
    }

    /**
     * Show widget with animation
     */
    function showWidget() {
        setTimeout(() => {
            if (widgetButton) {
                widgetButton.classList.add('uc-show');
            }
        }, 1000); // Delay for better UX
    }

    /**
     * Hide widget
     */
    function hideWidget() {
        if (widgetButton) {
            widgetButton.classList.remove('uc-show');
        }
    }

    /**
     * Minimize chat (mobile)
     */
    function minimizeChat() {
        closeChat();
    }

    /**
     * Handle iframe ready event
     */
    function onChatReady() {
        console.log('University Chat Widget: Chat interface ready');
    }

    /**
     * Handle new message notification
     */
    function handleNewMessage(content) {
        if (!isOpen) {
            // Show notification
            showNotification();
        }
    }

    /**
     * Show new message notification
     */
    function showNotification() {
        widgetButton.classList.add('uc-has-notification');
        
        // Auto-remove notification after 5 seconds
        setTimeout(() => {
            widgetButton.classList.remove('uc-has-notification');
        }, 5000);
    }

    /**
     * Trap focus within modal for accessibility
     */
    function trapFocus() {
        const focusableElements = chatModal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        
        if (firstElement) {
            firstElement.focus();
        }
        
        chatModal.addEventListener('keydown', function(e) {
            if (e.key === 'Tab') {
                if (e.shiftKey) {
                    if (document.activeElement === firstElement) {
                        lastElement.focus();
                        e.preventDefault();
                    }
                } else {
                    if (document.activeElement === lastElement) {
                        firstElement.focus();
                        e.preventDefault();
                    }
                }
            }
            
            if (e.key === 'Escape') {
                closeChat();
            }
        });
    }

    /**
     * Track events for analytics
     */
    function trackEvent(eventName, data = {}) {
        // Send to analytics if available
        if (typeof gtag === 'function') {
            gtag('event', eventName, {
                event_category: 'University Chat Widget',
                university: config.university,
                ...data
            });
        }
        
        // Send to custom analytics endpoint
        try {
            fetch(`${config.apiUrl}/api/analytics/widget-event`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    event: eventName,
                    university: config.university,
                    timestamp: new Date().toISOString(),
                    url: window.location.href,
                    ...data
                })
            }).catch(() => {}); // Fail silently
        } catch (error) {
            // Fail silently
        }
    }

    /**
     * Inject CSS styles
     */
    function injectStyles() {
        if (document.getElementById('uc-widget-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'uc-widget-styles';
        style.textContent = getWidgetCSS();
        document.head.appendChild(style);
    }

    /**
     * Get widget CSS
     */
    function getWidgetCSS() {
        return `
            /* University Chat Widget Styles */
            :root {
                --uc-primary-color: ${config.primaryColor || '#0c3c8c'};
                --uc-secondary-color: ${config.secondaryColor || '#667eea'};
                --uc-text-color: #ffffff;
                --uc-shadow: 0 4px 16px rgba(0,0,0,0.15);
                --uc-border-radius: 50px;
                --uc-transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                --uc-z-index: ${config.zIndex};
            }
            
            .uc-widget-button {
                position: fixed;
                cursor: pointer;
                user-select: none;
                z-index: var(--uc-z-index);
                transition: var(--uc-transition);
                opacity: 0;
                transform: scale(0.8) translateY(20px);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            }
            
            .uc-widget-button.uc-show {
                opacity: 1;
                transform: scale(1) translateY(0);
            }
            
            .uc-widget-button.uc-hover {
                transform: scale(1.05) translateY(-2px);
            }
            
            .uc-widget-button.uc-position-bottom-right {
                bottom: 20px;
                right: 20px;
            }
            
            .uc-widget-button.uc-position-bottom-left {
                bottom: 20px;
                left: 20px;
            }
            
            .uc-widget-button.uc-position-top-right {
                top: 20px;
                right: 20px;
            }
            
            .uc-widget-button.uc-position-top-left {
                top: 20px;
                left: 20px;
            }
            
            .uc-button-content {
                background: linear-gradient(135deg, var(--uc-primary-color), var(--uc-secondary-color));
                color: var(--uc-text-color);
                border-radius: var(--uc-border-radius);
                box-shadow: var(--uc-shadow);
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                padding: 12px 20px;
                position: relative;
                overflow: hidden;
                transition: var(--uc-transition);
                min-height: 56px;
            }
            
            .uc-widget-button.uc-size-small .uc-button-content {
                padding: 12px;
                min-height: 48px;
                border-radius: 50%;
            }
            
            .uc-widget-button.uc-size-large .uc-button-content {
                padding: 16px 24px;
                min-height: 64px;
                font-size: 16px;
            }
            
            .uc-icon-container {
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
            }
            
            .uc-icon {
                transition: var(--uc-transition);
            }
            
            .uc-icon-close {
                display: none;
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
            }
            
            .uc-button-text {
                font-weight: 600;
                font-size: 14px;
                white-space: nowrap;
            }
            
            .uc-widget-button.uc-size-small .uc-button-text {
                display: none;
            }
            
            .uc-pulse-ring {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 100%;
                height: 100%;
                border: 2px solid var(--uc-primary-color);
                border-radius: inherit;
                animation: uc-pulse 2s infinite;
                pointer-events: none;
            }
            
            .uc-widget-button.uc-has-notification .uc-pulse-ring {
                border-color: #ff4757;
                animation-duration: 1s;
            }
            
            .uc-widget-button.uc-has-notification::after {
                content: '';
                position: absolute;
                top: -2px;
                right: -2px;
                width: 12px;
                height: 12px;
                background: #ff4757;
                border-radius: 50%;
                border: 2px solid white;
                animation: uc-bounce 0.6s ease-out;
            }
            
            @keyframes uc-pulse {
                0% {
                    transform: translate(-50%, -50%) scale(1);
                    opacity: 1;
                }
                100% {
                    transform: translate(-50%, -50%) scale(1.3);
                    opacity: 0;
                }
            }
            
            @keyframes uc-bounce {
                0%, 20%, 53%, 80%, 100% {
                    transform: scale(1);
                }
                40%, 43% {
                    transform: scale(1.3);
                }
                70% {
                    transform: scale(1.1);
                }
            }
            
            .uc-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(4px);
                z-index: var(--uc-z-index);
                opacity: 0;
                visibility: hidden;
                transition: var(--uc-transition);
            }
            
            .uc-overlay.uc-show {
                opacity: 1;
                visibility: visible;
            }
            
            .uc-modal {
                position: fixed;
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.2);
                z-index: calc(var(--uc-z-index) + 1);
                opacity: 0;
                visibility: hidden;
                transform: scale(0.9) translateY(20px);
                transition: var(--uc-transition);
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            
            .uc-modal.uc-show {
                opacity: 1;
                visibility: visible;
                transform: scale(1) translateY(0);
            }
            
            .uc-modal.uc-position-bottom-right {
                bottom: 100px;
                right: 20px;
                width: 400px;
                height: 600px;
            }
            
            .uc-modal.uc-position-bottom-left {
                bottom: 100px;
                left: 20px;
                width: 400px;
                height: 600px;
            }
            
            .uc-modal.uc-position-top-right {
                top: 100px;
                right: 20px;
                width: 400px;
                height: 600px;
            }
            
            .uc-modal.uc-position-top-left {
                top: 100px;
                left: 20px;
                width: 400px;
                height: 600px;
            }
            
            .uc-modal-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 16px 20px;
                background: linear-gradient(135deg, var(--uc-primary-color), var(--uc-secondary-color));
                color: white;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }
            
            .uc-header-info {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .uc-university-logo img {
                width: 40px;
                height: 40px;
                object-fit: contain;
                border-radius: 8px;
                background: rgba(255,255,255,0.1);
                padding: 4px;
            }
            
            .uc-header-text h3 {
                margin: 0;
                font-size: 16px;
                font-weight: 600;
                line-height: 1.2;
            }
            
            .uc-header-text p {
                margin: 0;
                font-size: 12px;
                opacity: 0.8;
                line-height: 1;
            }
            
            .uc-close-button {
                background: none;
                border: none;
                color: white;
                cursor: pointer;
                padding: 8px;
                border-radius: 8px;
                transition: var(--uc-transition);
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .uc-close-button:hover {
                background: rgba(255,255,255,0.1);
            }
            
            .uc-modal-body {
                flex: 1;
                position: relative;
                overflow: hidden;
            }
            
            .uc-loading-placeholder {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100%;
                gap: 16px;
                color: #666;
            }
            
            .uc-loading-spinner {
                width: 32px;
                height: 32px;
                border: 3px solid #f3f3f3;
                border-top: 3px solid var(--uc-primary-color);
                border-radius: 50%;
                animation: uc-spin 1s linear infinite;
            }
            
            @keyframes uc-spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .uc-iframe {
                width: 100%;
                height: 100%;
                border: none;
                display: none;
            }
            
            /* Mobile Responsive */
            @media (max-width: 768px) {
                .uc-widget-button.uc-position-bottom-right,
                .uc-widget-button.uc-position-bottom-left {
                    bottom: 16px;
                }
                
                .uc-widget-button.uc-position-bottom-right {
                    right: 16px;
                }
                
                .uc-widget-button.uc-position-bottom-left {
                    left: 16px;
                }
                
                .uc-modal {
                    width: 100% !important;
                    height: 100% !important;
                    top: 0 !important;
                    left: 0 !important;
                    right: 0 !important;
                    bottom: 0 !important;
                    border-radius: 0;
                    transform: translateY(100%);
                }
                
                .uc-modal.uc-show {
                    transform: translateY(0);
                }
                
                .uc-overlay {
                    background: transparent;
                    backdrop-filter: none;
                }
            }
            
            /* Dark mode support */
            @media (prefers-color-scheme: dark) {
                .uc-modal {
                    background: #1a1a1a;
                    color: white;
                }
                
                .uc-loading-placeholder {
                    color: #ccc;
                }
            }
            
            /* Accessibility improvements */
            @media (prefers-reduced-motion: reduce) {
                .uc-widget-button,
                .uc-modal,
                .uc-overlay,
                .uc-pulse-ring {
                    transition: none !important;
                    animation: none !important;
                }
            }
            
            /* High contrast mode */
            @media (prefers-contrast: high) {
                .uc-button-content {
                    border: 2px solid white;
                }
                
                .uc-modal {
                    border: 2px solid #000;
                }
            }
        `;
    }

    /**
     * Public API
     */
    const UniversityChatWidget = {
        init: init,
        open: openChat,
        close: closeChat,
        toggle: toggleChat,
        show: showWidget,
        hide: hideWidget,
        isOpen: () => isOpen,
        config: () => ({ ...config })
    };

    // Auto-initialize if script has data attributes
    if (document.currentScript && document.currentScript.hasAttribute('data-university')) {
        init();
    }

    // Global API
    window.UniversityChatWidget = UniversityChatWidget;

    // AMD/CommonJS support
    if (typeof define === 'function' && define.amd) {
        define(() => UniversityChatWidget);
    } else if (typeof module !== 'undefined' && module.exports) {
        module.exports = UniversityChatWidget;
    }

})();
