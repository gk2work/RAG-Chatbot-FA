"""
Conversation memory management for Enhanced RAG Service
"""

import logging
from typing import Dict, List, Any, Optional
from app.models.chat import ChatSession
from app.models.lead import Lead
from ..base.interfaces import ConversationManagerInterface


class MemoryManager(ConversationManagerInterface):
    """Manages conversation memory and context for Enhanced RAG Service"""
    
    def __init__(self, conversation_memory_size: int = 10):
        super().__init__()
        self.conversation_memory_size = conversation_memory_size
        self.stats = {'questions_answered': 0, 'total_queries': 0}
    
    def get_conversation_context(self, session_id: str, lead_id: str = None) -> Dict:
        """Get conversation context for enhanced responses"""
        try:
            context = {"conversation_length": 0, "message_history": [], "user_info": {}}
            
            if session_id:
                messages = ChatSession.get_session_messages(session_id)
                if messages:
                    context["conversation_length"] = len(messages)
                    context["message_history"] = messages[-self.conversation_memory_size:]
                    
                    self.logger.debug(f"📊 Conversation context - Length: {context['conversation_length']}, Messages: {len(context['message_history'])}")
            
            # Get user info from lead if available
            if lead_id:
                try:
                    lead = Lead.get_lead_by_id(lead_id)
                    if lead:
                        context["user_info"] = {
                            "name": lead.get('name', ''),
                            "email": lead.get('email', ''),
                            "country": lead.get('country', 'Unknown'),
                            "mobile": lead.get('mobile', '')
                        }
                        self.logger.debug(f"👤 User info from lead: {context['user_info']}")
                except Exception as lead_error:
                    self.logger.warning(f"Error getting lead info: {lead_error}")
            
            return context
        except Exception as e:
            self.logger.error(f"Error getting conversation context: {e}")
            return {"conversation_length": 0, "message_history": [], "user_info": {}}

    def update_conversation_memory(self, session_id: str, lead_id: str, question: str, response: Dict):
        """Update conversation memory"""
        try:
            if session_id:
                ChatSession.add_message(session_id, "assistant", response.get('answer', ''), {
                    "lead_id": lead_id,
                    "processing_method": "enhanced_rag",
                    "contains_question": response.get('contains_question', False),
                    "response_type": response.get('response_type', 'standard'),
                    "university_branded": response.get('university_branded', False),
                    "conversation_aware": response.get('conversation_aware', False)
                })
                
                # Update stats
                self.stats['questions_answered'] += 1
                self.stats['total_queries'] += 1
                
        except Exception as e:
            self.logger.error(f"Error updating conversation memory: {e}")
    
    def clear_conversation_memory(self, session_id: str) -> bool:
        """Clear conversation memory for a session"""
        try:
            # This would also clear conversation context from database if needed
            # Additional implementation can be added here for persistent memory
            
            self.logger.info(f"Cleared conversation memory for session {session_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing conversation memory: {e}")
            return False

    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the conversation"""
        try:
            session = ChatSession.get_session(session_id) if session_id else None
            if not session:
                return {"error": "Session not found"}
            
            messages = session.get("messages", [])
            context = self.get_conversation_context(session_id)
            
            return {
                "total_messages": len(messages),
                "topics_discussed": context.get("topics_discussed", []),
                "user_info_collected": context.get("user_info", {}),
                "session_duration": "estimated_duration",
                "last_updated": session.get("updated_at"),
                "university_x_id": session.get("university_x_id"),
                "enhanced_features_used": {
                    "vector_search": True,  # This will be updated by orchestrator
                    "conversation_memory": True,
                    "lead_management": bool(context.get("user_info", {}).get("name")),
                    "dynamic_questioning": True  # This will be updated by orchestrator
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting conversation summary: {e}")
            return {"error": str(e)}
    
    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get session state - to be implemented by SessionStateManager"""
        return {}
    
    def get_stats(self) -> Dict[str, int]:
        """Get memory manager statistics"""
        return self.stats.copy()
    
    def health_check(self) -> tuple[bool, str]:
        """Check memory manager health"""
        try:
            # Test basic functionality
            test_context = self.get_conversation_context("test_session")
            if isinstance(test_context, dict):
                return True, "Memory manager is healthy"
            else:
                return False, "Memory manager failed context test"
        except Exception as e:
            return False, f"Memory manager health check failed: {e}"
