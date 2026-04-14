/**
 * Build Configuration for University Chatbot Widget
 * This script helps build and optimize the widget for production deployment
 */

const fs = require('fs');
const path = require('path');
const { minify } = require('terser');

const CONFIG = {
    // Source files
    source: {
        main: './widget-loader.js',
        css: './widget-styles.css'
    },
    
    // Output directories
    output: {
        dev: './dist/dev/',
        prod: './dist/prod/',
        cdn: './dist/cdn/'
    },
    
    // Build options
    options: {
        minify: true,
        sourcemap: true,
        version: '1.0.0',
        banner: '/* University Chatbot Widget v{{VERSION}} | MIT License */'
    },
    
    // CDN configuration
    cdn: {
        baseUrl: 'https://cdn.university-chatbot.com',
        paths: {
            js: '/widget/{{VERSION}}/widget-loader.js',
            css: '/widget/{{VERSION}}/widget-styles.css'
        }
    }
};

/**
 * Build widget for different environments
 */
async function buildWidget() {
    console.log('🏗️  Building University Chatbot Widget...\n');
    
    try {
        // Ensure output directories exist
        createDirectories();
        
        // Read source files
        const jsContent = fs.readFileSync(CONFIG.source.main, 'utf8');
        
        // Build development version
        await buildDevelopment(jsContent);
        
        // Build production version
        await buildProduction(jsContent);
        
        // Build CDN version
        await buildCDN(jsContent);
        
        // Generate integration examples
        generateExamples();
        
        console.log('✅ Build completed successfully!\n');
        
    } catch (error) {
        console.error('❌ Build failed:', error);
        process.exit(1);
    }
}

/**
 * Create output directories
 */
function createDirectories() {
    Object.values(CONFIG.output).forEach(dir => {
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    });
}

/**
 * Build development version
 */
async function buildDevelopment(jsContent) {
    console.log('📦 Building development version...');
    
    // Add development configuration
    const devContent = jsContent.replace(
        /window\.location\.protocol \+ '\/\/localhost:5000'/g,
        'window.location.protocol + "//localhost:5000"'
    ).replace(
        /window\.location\.protocol \+ '\/\/localhost:4200'/g,
        'window.location.protocol + "//localhost:4200"'
    );
    
    // Add banner
    const banner = CONFIG.options.banner.replace('{{VERSION}}', CONFIG.options.version + '-dev');
    const finalContent = banner + '\n' + devContent;
    
    // Write development file
    fs.writeFileSync(path.join(CONFIG.output.dev, 'widget-loader.js'), finalContent);
    
    console.log('  ✓ Development build created');
}

/**
 * Build production version
 */
async function buildProduction(jsContent) {
    console.log('📦 Building production version...');
    
    // Replace development URLs with production URLs
    const prodContent = jsContent.replace(
        /window\.location\.protocol \+ '\/\/localhost:5000'/g,
        '"https://api.university-chatbot.com"'
    ).replace(
        /window\.location\.protocol \+ '\/\/localhost:4200'/g,
        '"https://chat.university-chatbot.com"'
    );
    
    if (CONFIG.options.minify) {
        console.log('  🗜️  Minifying JavaScript...');
        
        const minified = await minify(prodContent, {
            compress: {
                drop_console: true,
                drop_debugger: true,
                pure_funcs: ['console.log', 'console.warn']
            },
            mangle: {
                reserved: ['UniversityChatWidget']
            },
            format: {
                comments: false,
                preamble: CONFIG.options.banner.replace('{{VERSION}}', CONFIG.options.version)
            },
            sourceMap: CONFIG.options.sourcemap ? {
                filename: 'widget-loader.js',
                url: 'widget-loader.js.map'
            } : false
        });
        
        // Write minified file
        fs.writeFileSync(path.join(CONFIG.output.prod, 'widget-loader.js'), minified.code);
        
        if (minified.map) {
            fs.writeFileSync(path.join(CONFIG.output.prod, 'widget-loader.js.map'), minified.map);
        }
        
        console.log('  ✓ Minified production build created');
        
        // Log size information
        const originalSize = Buffer.byteLength(prodContent, 'utf8');
        const minifiedSize = Buffer.byteLength(minified.code, 'utf8');
        const compression = ((originalSize - minifiedSize) / originalSize * 100).toFixed(1);
        
        console.log(`  📊 Size: ${originalSize} → ${minifiedSize} bytes (${compression}% reduction)`);
        
    } else {
        // Add banner without minification
        const banner = CONFIG.options.banner.replace('{{VERSION}}', CONFIG.options.version);
        const finalContent = banner + '\n' + prodContent;
        
        fs.writeFileSync(path.join(CONFIG.output.prod, 'widget-loader.js'), finalContent);
        console.log('  ✓ Production build created (unminified)');
    }
}

/**
 * Build CDN version
 */
async function buildCDN(jsContent) {
    console.log('📦 Building CDN version...');
    
    // Use CDN URLs
    const cdnContent = jsContent.replace(
        /window\.location\.protocol \+ '\/\/localhost:5000'/g,
        `"${CONFIG.cdn.baseUrl}/api"`
    ).replace(
        /window\.location\.protocol \+ '\/\/localhost:4200'/g,
        `"${CONFIG.cdn.baseUrl}/chat"`
    );
    
    // Minify for CDN
    const minified = await minify(cdnContent, {
        compress: {
            drop_console: true,
            drop_debugger: true,
            pure_funcs: ['console.log', 'console.warn']
        },
        mangle: {
            reserved: ['UniversityChatWidget']
        },
        format: {
            comments: false,
            preamble: CONFIG.options.banner.replace('{{VERSION}}', CONFIG.options.version)
        }
    });
    
    // Write CDN file
    fs.writeFileSync(path.join(CONFIG.output.cdn, 'widget-loader.js'), minified.code);
    
    console.log('  ✓ CDN build created');
}

/**
 * Generate integration examples
 */
function generateExamples() {
    console.log('📝 Generating integration examples...');
    
    const examples = {
        // Basic HTML integration
        basic: `<!DOCTYPE html>
<html>
<head>
    <title>University Website</title>
</head>
<body>
    <h1>Welcome to Our University</h1>
    
    <!-- University Chatbot Widget -->
    <script src="${CONFIG.cdn.baseUrl}${CONFIG.cdn.paths.js.replace('{{VERSION}}', CONFIG.options.version)}" 
            data-university="csss" 
            data-position="bottom-right">
    </script>
</body>
</html>`,

        // WordPress integration
        wordpress: `<?php
// Add to your theme's functions.php file

function add_university_chat_widget() {
    $university_id = get_option('university_chat_id', 'csss');
    $position = get_option('university_chat_position', 'bottom-right');
    $version = '${CONFIG.options.version}';
    
    echo "<script src='${CONFIG.cdn.baseUrl}/widget/\$version/widget-loader.js' 
                  data-university='\$university_id' 
                  data-position='\$position'>
          </script>";
}
add_action('wp_footer', 'add_university_chat_widget');
?>`,

        // React integration
        react: `import { useEffect } from 'react';

function UniversityChatWidget({ university = 'csss', position = 'bottom-right' }) {
    useEffect(() => {
        const script = document.createElement('script');
        script.src = '${CONFIG.cdn.baseUrl}${CONFIG.cdn.paths.js.replace('{{VERSION}}', CONFIG.options.version)}';
        script.setAttribute('data-university', university);
        script.setAttribute('data-position', position);
        document.body.appendChild(script);
        
        return () => {
            if (script.parentNode) {
                script.parentNode.removeChild(script);
            }
        };
    }, [university, position]);
    
    return null;
}

export default UniversityChatWidget;`,

        // Vue.js integration
        vue: `<template>
  <div id="app">
    <!-- Your app content -->
  </div>
</template>

<script>
export default {
    name: 'App',
    mounted() {
        this.loadChatWidget();
    },
    methods: {
        loadChatWidget() {
            const script = document.createElement('script');
            script.src = '${CONFIG.cdn.baseUrl}${CONFIG.cdn.paths.js.replace('{{VERSION}}', CONFIG.options.version)}';
            script.setAttribute('data-university', 'csss');
            script.setAttribute('data-position', 'bottom-right');
            document.body.appendChild(script);
        }
    }
};
</script>`,

        // Advanced JavaScript integration
        advanced: `// Advanced integration with custom configuration
document.addEventListener('DOMContentLoaded', function() {
    // Load widget script dynamically
    const script = document.createElement('script');
    script.src = '${CONFIG.cdn.baseUrl}${CONFIG.cdn.paths.js.replace('{{VERSION}}', CONFIG.options.version)}';
    script.onload = function() {
        // Initialize with custom configuration
        UniversityChatWidget.init({
            university: 'csss',
            position: 'bottom-right',
            size: 'medium',
            theme: '#0c3c8c',
            showOnLoad: true,
            pulseAnimation: true
        });
        
        // Set up event listeners
        window.addEventListener('message', function(event) {
            if (event.data.type === 'widget_opened') {
                console.log('Chat widget opened');
                // Track with analytics
                gtag('event', 'chat_opened', {
                    event_category: 'engagement'
                });
            }
        });
    };
    document.head.appendChild(script);
});`
    };
    
    // Write example files
    Object.entries(examples).forEach(([name, content]) => {
        const extension = name === 'wordpress' ? 'php' : 
                         name === 'react' || name === 'vue' ? 'jsx' : 
                         'html';
        
        fs.writeFileSync(
            path.join(CONFIG.output.prod, `example-${name}.${extension}`),
            content
        );
    });
    
    console.log('  ✓ Integration examples generated');
}

/**
 * Generate package.json for npm publishing
 */
function generatePackageJson() {
    const packageJson = {
        name: '@university-chatbot/widget',
        version: CONFIG.options.version,
        description: 'Embeddable university chatbot widget',
        main: 'widget-loader.js',
        types: 'widget-loader.d.ts',
        files: ['widget-loader.js', 'widget-loader.d.ts', 'README.md'],
        keywords: ['chatbot', 'university', 'widget', 'ai', 'customer-support'],
        author: 'University Chatbot Team',
        license: 'MIT',
        homepage: 'https://university-chatbot.com',
        repository: {
            type: 'git',
            url: 'https://github.com/university-chatbot/widget.git'
        },
        bugs: {
            url: 'https://github.com/university-chatbot/widget/issues'
        }
    };
    
    fs.writeFileSync(
        path.join(CONFIG.output.prod, 'package.json'),
        JSON.stringify(packageJson, null, 2)
    );
}

/**
 * Generate TypeScript definitions
 */
function generateTypeDefinitions() {
    const types = `/**
 * University Chatbot Widget TypeScript Definitions
 */

export interface WidgetConfig {
    university: string;
    position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
    size?: 'small' | 'medium' | 'large';
    theme?: string;
    customText?: string;
    customIcon?: string;
    showOnLoad?: boolean;
    pulseAnimation?: boolean;
    soundEnabled?: boolean;
    apiUrl?: string;
    chatUrl?: string;
    zIndex?: number;
}

export interface UniversityChatWidget {
    init(config: WidgetConfig): void;
    open(): void;
    close(): void;
    toggle(): void;
    show(): void;
    hide(): void;
    isOpen(): boolean;
    config(): WidgetConfig;
}

declare global {
    interface Window {
        UniversityChatWidget: UniversityChatWidget;
    }
}

export default UniversityChatWidget;`;
    
    fs.writeFileSync(
        path.join(CONFIG.output.prod, 'widget-loader.d.ts'),
        types
    );
}

// Run build if this script is executed directly
if (require.main === module) {
    buildWidget().then(() => {
        generatePackageJson();
        generateTypeDefinitions();
        
        console.log('🎉 Build process completed successfully!');
        console.log('\nFiles generated:');
        console.log('  📁 dist/dev/widget-loader.js (development)');
        console.log('  📁 dist/prod/widget-loader.js (production)');
        console.log('  📁 dist/cdn/widget-loader.js (CDN ready)');
        console.log('  📁 dist/prod/example-*.* (integration examples)');
        console.log('  📁 dist/prod/package.json (npm package)');
        console.log('  📁 dist/prod/widget-loader.d.ts (TypeScript definitions)');
    });
}

module.exports = { buildWidget, CONFIG };
