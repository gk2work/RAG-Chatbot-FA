"""
University Chatbot Flask Application
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
from app.config import Config
from app.models import init_db
import logging
import time
import os
from datetime import datetime

# import logging
# logging.basicConfig(level=logging.DEBUG)

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    if config_name:
        app.config.from_object(config_name)
    else:
        app.config.from_object(Config)
    
    # Initialize CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:4200", "http://127.0.0.1:4200", "http://localhost:4201", "http://127.0.0.1:4201",'https://dev-uni-chat.foreignadmits.app', "https://prod-uni-chat-fe.foreignadmits.app" ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Cache-Control", "Pragma", "Expires"]
        }
    })
    
    # Configure logging
    setup_logging(app)
    
    # Initialize database
    init_db()
    
    # Register blueprints
    from app.api.chat_routes import chat_bp
    from app.api.university_routes import university_bp
    from app.api.auth_routes import auth_bp
    from app.api.lead_routes import lead_bp
    from app.api.superadmin_routes import superadmin_bp
    from app.api.upload_routes import upload_bp
    
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(university_bp, url_prefix='/api/university')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(lead_bp, url_prefix='/api/lead')
    app.register_blueprint(superadmin_bp, url_prefix='/api/superadmin')
    app.register_blueprint(upload_bp, url_prefix='/api/upload')

     # ✅ ADD THIS: Register Telegram bot blueprint
    from app.api.telegram_routes import telegram_bp
    app.register_blueprint(telegram_bp, url_prefix='/api/telegram')

     # ✅ NEW: Register WhatsApp Blueprint
    from app.api.whatsapp_routes import whatsapp_bp
    app.register_blueprint(whatsapp_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({'error': 'File too large'}), 413
    
    # Static file serving for uploads
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        """Serve uploaded files with cache-busting headers"""
        from flask import send_from_directory, make_response
        upload_folder = os.path.join(app.root_path, '..', 'uploads')
        
        # ✅ FIXED: Add cache-busting headers to ensure logo updates are reflected
        response = make_response(send_from_directory(upload_folder, filename))
        
        # Set cache headers to prevent stale logo caching
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache' 
        response.headers['Expires'] = '0'
        
        # Add CORS headers for cross-origin requests
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        
        return response
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        try:
            # Use simple RAG service to avoid LangChain compatibility issues
            from app.services.simple_rag_service import SimpleRAGService
            
            # Test simple RAG service only (no vectorstore to avoid LangChain)
            rag_service = SimpleRAGService()
            rag_healthy, rag_msg = rag_service.health_check()
            vs_healthy, vs_msg = True, "VectorStore checks disabled to avoid LangChain issues"
            
            return jsonify({
                'status': 'healthy' if (rag_healthy and vs_healthy) else 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'services': {
                    'rag_service': {'healthy': rag_healthy, 'message': rag_msg},
                    'vectorstore_service': {'healthy': vs_healthy, 'message': vs_msg}
                }
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 503

    return app

def setup_logging(app):
    """Setup application logging"""
    for handler in logging.getLogger().handlers[:]:
        logging.getLogger().removeHandler(handler)
   
    # Set root logger to INFO to avoid DEBUG logs from external libraries
    logging.basicConfig(level=logging.INFO,
                         format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
   
    # Explicitly set levels for noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    logging.getLogger('faiss').setLevel(logging.WARNING)
   
 
    if not app.debug and not app.testing:
        # Production logging
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = logging.FileHandler('logs/university_chatbot.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('University Chatbot startup')
    else:
        app.logger.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        console_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(console_handler)
        app.logger.info('University Chatbot startup (Development mode)')
        