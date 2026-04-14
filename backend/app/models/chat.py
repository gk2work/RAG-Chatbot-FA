"""
Enhanced Chat Model with Complete Message Storage and X-ID Support
Addresses requirement A: All messages saved in backend
"""

from app.models import chat_sessions_collection, universities_collection
from bson import ObjectId
from datetime import datetime
import hashlib
import base64
from datetime import timedelta
import logging

class ChatSession:
    @staticmethod
    def generate_x_id(university_code):
        """
        Generate a deterministic 8-character alphanumeric X ID based on university_code
        This ensures the same university always gets the same X ID
        """
        # Create hash of university_code
        hash_object = hashlib.sha256(university_code.encode())
        hash_hex = hash_object.hexdigest()
        
        # Convert to base64 and take first 8 alphanumeric characters
        hash_b64 = base64.b64encode(bytes.fromhex(hash_hex)).decode('ascii')
        
        # Filter to alphanumeric only and take first 8 characters
        x_id = ''.join(c for c in hash_b64 if c.isalnum())[:8].upper()
        
        return f"X{x_id}"
    
    @staticmethod
    def create_session(university_code, user_id=None):
        """Create a new chat session with X-ID integration"""
        # Get university info to validate and get X-ID
        university = universities_collection.find_one({"code": university_code.lower()})
        
        if not university:
            raise ValueError(f"University with code '{university_code}' not found")
        
        # Get or generate X-ID
        university_x_id = university.get('x_id')
        if not university_x_id:
            university_x_id = ChatSession.generate_x_id(university_code)
            # Update university with X-ID
            universities_collection.update_one(
                {"code": university_code.lower()},
                {"$set": {"x_id": university_x_id}}
            )
        
        session_data = {
            "university_code": university_code.lower(),
            "university_x_id": university_x_id,  # Store X-ID
            "university_name": university.get('name'),  # Store name for easy access
            "user_id": user_id,
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True,
            "message_count": 0
        }
        result = chat_sessions_collection.insert_one(session_data)
        return str(result.inserted_id)
    
    @staticmethod
    def create_session_by_x_id(university_x_id, user_id=None):
        """Create a new chat session using X-ID"""
        # Get university info by X-ID
        university = universities_collection.find_one({"x_id": university_x_id.upper()})
        
        if not university:
            raise ValueError(f"University with X-ID '{university_x_id}' not found")
        
        session_data = {
            "university_code": university.get('code'),
            "university_x_id": university_x_id.upper(),
            "university_name": university.get('name'),
            "user_id": user_id,
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True,
            "message_count": 0
        }
        result = chat_sessions_collection.insert_one(session_data)
        return str(result.inserted_id)
    
    @staticmethod
    def add_message(session_id, message_type, content, metadata=None):
        """Add a message to the chat session AND automatically store in lead's complete history"""
        try:
            message = {
                "type": message_type,  # "user" or "assistant"
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow(),
                "message_id": str(ObjectId())  # Unique ID for each message
            }
        
            # Update session with new message and increment message count
            result = chat_sessions_collection.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$push": {"messages": message},
                    "$set": {"updated_at": datetime.utcnow()},
                    "$inc": {"message_count": 1}
                }
            )
        
            # ✅ FIXED: CRITICAL - Also store in lead's complete history
            lead_id = None
            university_x_id = None
        
            # Extract lead_id from metadata if provided
            if metadata:
                lead_id = metadata.get('lead_id')
                university_x_id = metadata.get('university_x_id')
        
            # ✅ FIXED: If no lead_id in metadata, try to get it from session
            if not lead_id:
                try:
                    session = chat_sessions_collection.find_one({"_id": ObjectId(session_id)})
                    if session:
                        # Check if session has user_id that might be a lead_id
                        session_user_id = session.get('user_id')
                        university_x_id = session.get('university_x_id')
                    
                        # For public sessions, user_id might be None, but we could have lead info
                        if session_user_id:
                            lead_id = session_user_id
                    
                        logging.debug(f"Session info: user_id={session_user_id}, university_x_id={university_x_id}")
                except Exception as session_error:
                    logging.warning(f"Could not retrieve session info: {session_error}")
        
            # ✅ FIXED: Store in lead's complete history if we have a lead_id
            if lead_id:
                try:
                    # Import Lead here to avoid circular imports
                    from app.models.lead import Lead
                
                    # Enhanced metadata for lead storage
                    lead_metadata = {
                        **(metadata or {}),
                        "session_id": session_id,
                        "university_x_id": university_x_id,
                        "message_id": message["message_id"],
                        "stored_in_session": True,
                        "timestamp": message["timestamp"]
                    }
                
                    # Store in lead's complete chat history
                    success = Lead.add_complete_message(
                        lead_id=lead_id,
                        session_id=session_id,
                        message_type=message_type,
                        content=content,
                        metadata=lead_metadata
                    )
                
                    if success:
                        logging.info(f"✅ Message stored in lead {lead_id} complete history: {message_type} - '{content[:50]}...'")
                    else:
                        logging.warning(f"❌ Failed to store message in lead {lead_id} complete history")
                    
                except Exception as lead_error:
                    logging.error(f"❌ Error storing message in lead complete history: {lead_error}")
            else:
                logging.debug(f"No lead_id found for session {session_id}, message stored in session only")
        
            return result.modified_count > 0
        
        except Exception as e:
            logging.error(f"Error adding message to session {session_id}: {e}")
            return False
        
    @staticmethod
    def link_session_to_lead(session_id, lead_id):
        """Link an existing session to a lead (for retroactive linking)"""
        try:
            # Update session to include lead reference
            result = chat_sessions_collection.update_one(
                {"_id": ObjectId(session_id)},
                {
                    "$set": {
                        "lead_id": lead_id,  # Add lead reference to session
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        
            if result.modified_count > 0:
                logging.info(f"✅ Session {session_id} linked to lead {lead_id}")
            
                # ✅ FIXED: Retroactively store existing messages in lead's complete history
                try:
                    from app.models.lead import Lead
                
                    session = chat_sessions_collection.find_one({"_id": ObjectId(session_id)})
                    if session and session.get('messages'):
                        messages = session.get('messages', [])
                        university_x_id = session.get('university_x_id')
                    
                        for msg in messages:
                            enhanced_metadata = {
                                **(msg.get('metadata') or {}),
                                "session_id": session_id,
                                "university_x_id": university_x_id,
                                "message_id": msg.get('message_id'),
                                "retroactive_link": True,
                                "original_timestamp": msg.get('timestamp')
                            }
                        
                            Lead.add_complete_message(
                                lead_id=lead_id,
                                session_id=session_id,
                                message_type=msg.get('type'),
                                content=msg.get('content'),
                                metadata=enhanced_metadata
                            )
                    
                        logging.info(f"✅ Retroactively stored {len(messages)} messages in lead {lead_id}")
                    
                except Exception as retroactive_error:
                    logging.error(f"Error in retroactive message storage: {retroactive_error}")
        
            return result.modified_count > 0
        
        except Exception as e:
            logging.error(f"Error linking session {session_id} to lead {lead_id}: {e}")
            return False    
    
    @staticmethod
    def get_session(session_id):
        """Get a chat session by ID"""
        try:
            return chat_sessions_collection.find_one({"_id": ObjectId(session_id)})
        except:
            return None
    
    @staticmethod
    def get_session_messages(session_id, limit=None):
        """Get messages from a chat session"""
        try:
            session = chat_sessions_collection.find_one({"_id": ObjectId(session_id)})
            if not session:
                return []
            
            messages = session.get("messages", [])
            if limit:
                messages = messages[-limit:]  # Get last N messages
            
            return messages
        except:
            return []
    
    @staticmethod
    def get_complete_session_history(session_id):
        """Get complete session history with enhanced metadata"""
        try:
            session = chat_sessions_collection.find_one({"_id": ObjectId(session_id)})
            if not session:
                return None
            
            messages = session.get("messages", [])
            
            return {
                "session_id": session_id,
                "university_x_id": session.get("university_x_id"),
                "university_name": session.get("university_name"),
                "university_code": session.get("university_code"),
                "user_id": session.get("user_id"),
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at"),
                "is_active": session.get("is_active", True),
                "total_messages": len(messages),
                "messages": messages,
                "message_statistics": {
                    "user_messages": len([m for m in messages if m.get("type") == "user"]),
                    "assistant_messages": len([m for m in messages if m.get("type") == "assistant"]),
                    "first_message_time": messages[0].get("timestamp") if messages else None,
                    "last_message_time": messages[-1].get("timestamp") if messages else None
                }
            }
        except Exception as e:
            logging.error(f"Error getting complete session history: {str(e)}")
            return None
    
    @staticmethod
    def get_sessions_by_user(user_id, limit=10):
        """Get chat sessions for a specific user"""
        return list(chat_sessions_collection.find({
            "user_id": user_id
        }).sort("created_at", -1).limit(limit))
    
    # SOLUTION B: Get sessions by X-ID for admin filtering
    @staticmethod
    def get_sessions_by_university_x_id(university_x_id, limit=10):
        """Get chat sessions for a specific university X-ID - for admin dashboard"""
        try:
            return list(chat_sessions_collection.find({
                "university_x_id": university_x_id.upper()
            }).sort("created_at", -1).limit(limit))
        except Exception as e:
            logging.error(f"Error getting sessions by X-ID {university_x_id}: {str(e)}")
            return []
    
    @staticmethod
    def get_sessions_by_university_code(university_code, limit=10):
        """Get chat sessions for a specific university code"""
        return list(chat_sessions_collection.find({
            "university_code": university_code.lower()
        }).sort("created_at", -1).limit(limit))
    
    @staticmethod
    def get_sessions_by_user_and_university_x_id(user_id, university_x_id, limit=10):
        """Get sessions for a user at a specific university"""
        return list(chat_sessions_collection.find({
            "user_id": user_id,
            "university_x_id": university_x_id.upper()
        }).sort("created_at", -1).limit(limit))
    
    @staticmethod
    def end_session(session_id):
        """Mark a chat session as inactive"""
        return chat_sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "is_active": False,
                    "ended_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        ).modified_count > 0
    
    @staticmethod
    def delete_session(session_id):
        """Delete a chat session completely"""
        try:
            result = chat_sessions_collection.delete_one({"_id": ObjectId(session_id)})
            return result.deleted_count > 0
        except:
            return False
    
    @staticmethod
    def get_session_summary(session_id):
        """Get a summary of a chat session with enhanced analytics"""
        try:
            session = chat_sessions_collection.find_one({"_id": ObjectId(session_id)})
            if not session:
                return None
            
            messages = session.get("messages", [])
            user_messages = [msg for msg in messages if msg.get("type") == "user"]
            assistant_messages = [msg for msg in messages if msg.get("type") == "assistant"]
            
            # Enhanced analytics
            topics_discussed = []
            for msg in user_messages:
                content = msg.get('content', '').lower()
                if 'admission' in content: topics_discussed.append('admissions')
                if 'program' in content or 'course' in content: topics_discussed.append('programs')
                if 'fee' in content or 'cost' in content: topics_discussed.append('fees')
                if 'facility' in content or 'campus' in content: topics_discussed.append('facilities')
            
            return {
                "session_id": str(session["_id"]),
                "university_code": session.get("university_code"),
                "university_x_id": session.get("university_x_id"),
                "university_name": session.get("university_name"),
                "user_id": session.get("user_id"),
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at"),
                "is_active": session.get("is_active", True),
                "total_messages": len(messages),
                "user_messages": len(user_messages),
                "assistant_messages": len(assistant_messages),
                "topics_discussed": list(set(topics_discussed)),
                "session_duration_minutes": ChatSession._calculate_session_duration(messages),
                "engagement_level": ChatSession._calculate_engagement_level(len(messages))
            }
        except Exception as e:
            logging.error(f"Error getting session summary: {str(e)}")
            return None
    
    @staticmethod
    def _calculate_session_duration(messages):
        """Calculate session duration in minutes"""
        if len(messages) < 2:
            return 0
        
        first_msg = messages[0].get('timestamp')
        last_msg = messages[-1].get('timestamp')
        
        if first_msg and last_msg:
            duration = last_msg - first_msg
            return int(duration.total_seconds() / 60)
        
        return 0
    
    @staticmethod
    def _calculate_engagement_level(message_count):
        """Calculate engagement level based on message count"""
        if message_count >= 20:
            return "high"
        elif message_count >= 10:
            return "medium"
        elif message_count >= 4:
            return "low"
        else:
            return "minimal"
    
    @staticmethod
    def get_sessions_created_today():
        """Get sessions created today - for health checks"""
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            return chat_sessions_collection.count_documents({"created_at": {"$gte": today_start}})
        except:
            return 0
    
    # SOLUTION B: University analytics by X-ID
    @staticmethod
    def get_university_session_analytics(university_x_id):
        """Get session analytics for a university by X-ID"""
        try:
            # Get all sessions for this university
            sessions = ChatSession.get_sessions_by_university_x_id(university_x_id, limit=1000)
            
            if not sessions:
                return {
                    "university_x_id": university_x_id,
                    "error": "No sessions found for this university"
                }
            
            # Calculate analytics
            total_sessions = len(sessions)
            active_sessions = sum(1 for s in sessions if s.get('is_active', True))
            total_messages = sum(s.get('message_count', 0) for s in sessions)
            
            # Engagement distribution
            engagement_levels = {"high": 0, "medium": 0, "low": 0, "minimal": 0}
            for session in sessions:
                msg_count = session.get('message_count', 0)
                level = ChatSession._calculate_engagement_level(msg_count)
                engagement_levels[level] += 1
            
            return {
                "university_x_id": university_x_id,
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_messages": total_messages,
                "average_messages_per_session": round(total_messages / total_sessions, 2) if total_sessions > 0 else 0,
                "engagement_distribution": engagement_levels,
                "last_updated": datetime.utcnow()
            }
            
        except Exception as e:
            logging.error(f"Error getting session analytics: {str(e)}")
            return {"error": str(e)}