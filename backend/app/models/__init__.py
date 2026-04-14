"""
Database models initialization
"""

from pymongo import MongoClient
from app.config import Config
import logging

# MongoDB connection
client = None
db = None
universities_collection = None
documents_collection = None
users_collection = None
conversations_collection = None
chat_sessions_collection = None
leads_collection = None
chunks_collection = None  # NEW: For PDF chunking and vector search

def init_db():
    """Initialize database connection"""
    global client, db, universities_collection, documents_collection, users_collection, conversations_collection, chat_sessions_collection, leads_collection, chunks_collection
    
    try:
        # Connect to MongoDB
        client = MongoClient(Config.MONGODB_URI)
        db = client[Config.MONGODB_DB_NAME]
        
        # Initialize collections
        universities_collection = db.universities
        documents_collection = db.documents
        users_collection = db.users
        conversations_collection = db.conversations
        chat_sessions_collection = db.chat_sessions
        leads_collection = db.leads
        chunks_collection = db.chunks  # NEW: PDF chunks collection
        
        # Create indexes for better performance
        universities_collection.create_index("code", unique=True)
        universities_collection.create_index("x_id", unique=True)
        documents_collection.create_index("university_code")
        documents_collection.create_index("university_x_id")
        chunks_collection.create_index("university_x_id")
        users_collection.create_index("email", unique=True)
        leads_collection.create_index("email", unique=True)
        leads_collection.create_index("university_code")
        
        # NEW: Chunks collection indexes for vector search
        chunks_collection.create_index([("university_x_id", 1), ("file_id", 1)])
        chunks_collection.create_index("chunk_id")
        chunks_collection.create_index("created_at")
        
        # New compound indexes for SuperAdmin functionality
        users_collection.create_index([("role", 1), ("is_active", 1)])  # Role-based queries
        users_collection.create_index([("created_by", 1), ("created_at", -1)])  # Sub-admin tracking
        chat_sessions_collection.create_index([("university_x_id", 1), ("created_at", -1)])  # University sessions
        chat_sessions_collection.create_index([("user_id", 1), ("is_active", 1)])  # User sessions
        leads_collection.create_index([("university_code", 1), ("created_at", -1)])  # University leads
        documents_collection.create_index([("university_x_id", 1), ("created_at", -1)])  # University documents
        
        logging.info("Database initialized successfully")
        
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        raise

def get_db():
    """Get database instance"""
    return db