"""
Session manager for bot platforms
Handles session creation and retrieval for Telegram, WhatsApp, Web
"""

import logging
from datetime import datetime
from bson import ObjectId

# Import models and get_db function
from app.models.chat import ChatSession
from app.models import get_db

logger = logging.getLogger(__name__)


class BotSessionManager:
    """Unified session management for all bot platforms"""
    
    @staticmethod
    def _get_sessions_collection():
        """Get chat_sessions collection (lazy loading)"""
        db = get_db()
        return db['chat_sessions']
    
    @staticmethod
    def get_or_create_session(
        platform: str,  # 'telegram', 'whatsapp', 'web'
        user_identifier: str,  # telegram_user_id or phone_number
        university_x_id: str,
        user_metadata: dict = None
    ) -> tuple:
        """
        Get existing session or create new one
        Returns: (session_id, is_new_session)
        """
        try:
            # Get collection dynamically
            chat_sessions_collection = BotSessionManager._get_sessions_collection()
            
            # Look for existing active session
            query = {
                'channel': platform,
                'is_active': True,
                'university_x_id': university_x_id
            }
            
            if platform == 'telegram':
                query['telegram_user_id'] = user_identifier
            elif platform == 'whatsapp':
                query['whatsapp_number'] = user_identifier
            
            existing_session = chat_sessions_collection.find_one(query)
            
            if existing_session:
                logger.info(f"Found existing {platform} session: {existing_session['_id']}")
                return str(existing_session['_id']), False
            
            # Create new session
            # Get university directly from database
            db = get_db()
            universities_collection = db['universities']
            university = universities_collection.find_one({'x_id': university_x_id})
            
            if not university:
                logger.error(f"University not found: {university_x_id}")
                raise ValueError(f"University not found: {university_x_id}")
            
            session_data = {
                'user_id': None,  # Public session
                'university_code': university.get('code'),
                'university_x_id': university_x_id,
                'channel': platform,
                'is_active': True,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'messages': []
            }
            
            # Add platform-specific identifiers
            if platform == 'telegram':
                session_data['telegram_user_id'] = user_identifier
                if user_metadata:
                    session_data['telegram_username'] = user_metadata.get('username')
                    session_data['telegram_first_name'] = user_metadata.get('first_name')
                    session_data['telegram_last_name'] = user_metadata.get('last_name')
            elif platform == 'whatsapp':
                session_data['whatsapp_number'] = user_identifier
                if user_metadata:
                    session_data['whatsapp_name'] = user_metadata.get('name')
            
            result = chat_sessions_collection.insert_one(session_data)
            session_id = str(result.inserted_id)
            
            logger.info(f"Created new {platform} session: {session_id}")
            return session_id, True
            
        except Exception as e:
            logger.error(f"Error in get_or_create_session: {e}")
            raise
    
    @staticmethod
    def get_session(session_id: str) -> dict:
        """Get session by ID"""
        return ChatSession.get_session(session_id)
    
    @staticmethod
    def update_session_activity(session_id: str):
        """Update last activity timestamp"""
        try:
            chat_sessions_collection = BotSessionManager._get_sessions_collection()
            chat_sessions_collection.update_one(
                {'_id': ObjectId(session_id)},
                {'$set': {'updated_at': datetime.utcnow()}}
            )
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")
    
    @staticmethod
    def link_lead_to_session(session_id: str, lead_id: str):
        """Link a lead to a session"""
        try:
            chat_sessions_collection = BotSessionManager._get_sessions_collection()
            chat_sessions_collection.update_one(
                {'_id': ObjectId(session_id)},
                {
                    '$set': {
                        'lead_id': lead_id,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            logger.info(f"Linked lead {lead_id} to session {session_id}")
        except Exception as e:
            logger.error(f"Error linking lead to session: {e}")
    
    @staticmethod
    def add_message_to_session(session_id: str, role: str, content: str):
        """Add message to session history"""
        try:
            chat_sessions_collection = BotSessionManager._get_sessions_collection()
            message = {
                'role': role,
                'content': content,
                'timestamp': datetime.utcnow()
            }
            chat_sessions_collection.update_one(
                {'_id': ObjectId(session_id)},
                {
                    '$push': {'messages': message},
                    '$set': {'updated_at': datetime.utcnow()}
                }
            )
        except Exception as e:
            logger.error(f"Error adding message to session: {e}")