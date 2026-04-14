"""
Configuration settings for the University Chatbot - OPTIMIZED VERSION
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the application"""
    
   # MongoDB Configuration
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://fadevadmin:c65q7FJC1iYPQ27G@cluster1.l2usi17.mongodb.net/rag_university_db')
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'rag_university_db')
    
    # OpenAI Configuration - OPTIMIZED
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')  # For main responses
    EXTRACTION_MODEL = os.getenv('EXTRACTION_MODEL', 'gpt-3.5-turbo')  # Cheaper for extractions
    
    # Vector Store Configuration
    VECTOR_STORE_TYPE = os.getenv('VECTOR_STORE_TYPE', 'faiss')  # faiss, chroma, mongodb
    FAISS_INDEX_PATH = os.getenv('FAISS_INDEX_PATH', './data/faiss_index')
    CHROMA_PERSIST_DIR = os.getenv('CHROMA_PERSIST_DIR', './data/chroma_db')
    
    # LLM Settings - OPTIMIZED
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.7'))
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', '3000'))  # Reduced from 10000
    EXTRACTION_MAX_TOKENS = int(os.getenv('EXTRACTION_MAX_TOKENS', '150'))  # For extractions only
    
    # OPTIMIZATION: Response Caching Settings
    ENABLE_RESPONSE_CACHE = os.getenv('ENABLE_RESPONSE_CACHE', 'True').lower() == 'true'
    CACHE_TTL_SECONDS = int(os.getenv('CACHE_TTL_SECONDS', '3600'))  # 1 hour
    MAX_CACHE_SIZE = int(os.getenv('MAX_CACHE_SIZE', '100'))  # Max cached responses
    
    # OPTIMIZATION: Smart Filtering Settings
    ENABLE_SMART_FILTERING = os.getenv('ENABLE_SMART_FILTERING', 'True').lower() == 'true'
    SKIP_EXTRACTION_FOR_SIMPLE_MESSAGES = os.getenv('SKIP_EXTRACTION_FOR_SIMPLE_MESSAGES', 'True').lower() == 'true'
    MINIMUM_MESSAGE_LENGTH = int(os.getenv('MINIMUM_MESSAGE_LENGTH', '3'))
    
    # Retrieval Settings - OPTIMIZED
    MAX_RETRIEVAL_DOCS = int(os.getenv('MAX_RETRIEVAL_DOCS', '3'))  # Reduced from 5 to save tokens
    RETRIEVAL_STRATEGY = os.getenv('RETRIEVAL_STRATEGY', 'similarity')  # similarity, mmr, similarity_score_threshold
    SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.7'))
    MMR_DIVERSITY_SCORE = float(os.getenv('MMR_DIVERSITY_SCORE', '0.3'))
    
    # Conversation Settings - OPTIMIZED
    CONVERSATION_MEMORY_SIZE = int(os.getenv('CONVERSATION_MEMORY_SIZE', '4'))  # Reduced from 6
    MAX_CONVERSATION_HISTORY_CHARS = int(os.getenv('MAX_CONVERSATION_HISTORY_CHARS', '200'))  # Per message
    MAX_DOCUMENT_CONTEXT_CHARS = int(os.getenv('MAX_DOCUMENT_CONTEXT_CHARS', '1500'))  # Document context limit
    
    # Document Processing
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '200'))
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # File Upload Settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    MAX_DOCUMENT_SIZE = int(os.getenv('MAX_DOCUMENT_SIZE', '300000'))  # 300,000 characters for document content
    
    # Advanced Features (Optional)
    ENABLE_COMPRESSION = os.getenv('ENABLE_COMPRESSION', 'False').lower() == 'true'
    ENABLE_MULTI_QUERY = os.getenv('ENABLE_MULTI_QUERY', 'False').lower() == 'true'
    
    # Embedding Model (for HuggingFace fallback)
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    
    # LangChain Settings
    LANGCHAIN_VERBOSE = os.getenv('LANGCHAIN_VERBOSE', 'False').lower() == 'true'
    
    # OPTIMIZATION: Cost Monitoring Settings
    ENABLE_API_CALL_LOGGING = os.getenv('ENABLE_API_CALL_LOGGING', 'True').lower() == 'true'
    LOG_TOKEN_USAGE = os.getenv('LOG_TOKEN_USAGE', 'True').lower() == 'true'
    WARN_ON_HIGH_TOKEN_USAGE = os.getenv('WARN_ON_HIGH_TOKEN_USAGE', 'True').lower() == 'true'
    HIGH_TOKEN_USAGE_THRESHOLD = int(os.getenv('HIGH_TOKEN_USAGE_THRESHOLD', '5000'))  # Per request


    # NEW: Bot Configuration
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_WEBHOOK_URL = os.environ.get('TELEGRAM_WEBHOOK_URL')
    
     # ✅ WhatsApp Configuration
    WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID')
    WHATSAPP_ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN')
    WHATSAPP_VERIFY_TOKEN = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'my_verify_token_12345')
    WHATSAPP_API_VERSION = os.environ.get('WHATSAPP_API_VERSION', 'v21.0')
    
    DEFAULT_UNIVERSITY_X_ID = os.environ.get('DEFAULT_UNIVERSITY_X_ID', 'XNR35QWNP')
    BOT_WEBHOOK_SECRET = os.environ.get('BOT_WEBHOOK_SECRET', 'change_this_secret')