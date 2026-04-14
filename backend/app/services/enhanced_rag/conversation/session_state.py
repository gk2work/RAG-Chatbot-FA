"""
Session state management for Enhanced RAG Service
"""

import logging
from typing import Dict, Any, Optional
from ..base.interfaces import BaseRAGComponent


class SessionStateManager(BaseRAGComponent):
    """Manages session state and questioning state for Enhanced RAG Service"""
    
    def __init__(self):
        super().__init__()
        self.session_question_state = {}
        
        # Questioning configuration
        self.questioning_config = {
            "max_failed_attempts": 2,
            "question_cooldown_turns": 2,
            "enable_dynamic_questioning": True,
            "ask_questions_every_n_turns": 2,
            "max_questions_per_conversation": 7
        }
        
        # Sequential questioning configuration
        self.question_sequence = [
            {"category": "user_name", "priority": 1, "required": True, "conversation_turn": 1},
            {"category": "educational_background", "priority": 2, "required": True, "conversation_turn": 2},
            {"category": "user_email", "priority": 3, "required": True, "conversation_turn": 4},
            {"category": "user_country", "priority": 4, "required": True, "conversation_turn": 6},
            {"category": "academic_interests", "priority": 5, "required": False, "conversation_turn": 8},
            {"category": "career_goals", "priority": 6, "required": False, "conversation_turn": 10}
        ]
    
    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get current state for a session"""
        try:
            if session_id in self.session_question_state:
                return self.session_question_state[session_id].copy()
            return {}
        except Exception as e:
            self.logger.error(f"Error getting session state: {e}")
            return {}
    
    def update_session_state(self, session_id: str, state_update: Dict[str, Any]):
        """Update session state"""
        try:
            if session_id not in self.session_question_state:
                self.session_question_state[session_id] = {
                    "questions_asked": [],
                    "last_question_turn": 0,
                    "failed_attempts": {},
                    "phase": 1
                }
            
            self.session_question_state[session_id].update(state_update)
            self.logger.debug(f"Updated session state for {session_id}: {state_update}")
            
        except Exception as e:
            self.logger.error(f"Error updating session state: {e}")
    
    def initialize_session_state(self, session_id: str):
        """Initialize session state for a new session"""
        try:
            if session_id not in self.session_question_state:
                self.session_question_state[session_id] = {
                    "questions_asked": [],
                    "last_question_turn": 0,
                    "failed_attempts": {},
                    "phase": 1
                }
                self.logger.info(f"Initialized session state for {session_id}")
        except Exception as e:
            self.logger.error(f"Error initializing session state: {e}")
    
    def reset_session_state(self, session_id: str) -> bool:
        """Reset questioning state for a session"""
        try:
            if session_id in self.session_question_state:
                del self.session_question_state[session_id]
                self.logger.info(f"Reset session state for {session_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error resetting session state: {e}")
            return False
    
    def update_question_state_on_response(self, session_id: str, question_asked: str, user_response: str):
        """Update question state tracking when user responds to a question"""
        try:
            if session_id in self.session_question_state:
                state = self.session_question_state[session_id]
                
                # Update the last question asked and response
                state["last_question_asked"] = question_asked
                state["last_user_response"] = user_response
                state["last_question_turn"] = state.get("conversation_turn", 0)
                
                self.logger.debug(f"Updated question state for session {session_id}")
                
        except Exception as e:
            self.logger.error(f"Error updating question state: {e}")
    
    def get_questioning_config(self) -> Dict[str, Any]:
        """Get questioning configuration"""
        return self.questioning_config.copy()
    
    def get_question_sequence(self) -> list:
        """Get question sequence configuration"""
        return self.question_sequence.copy()
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        return len(self.session_question_state)
    
    def clean_expired_sessions(self, max_age_hours: int = 24):
        """Clean up expired session states"""
        try:
            # This would implement session cleanup logic based on age
            # For now, just log the operation
            self.logger.info(f"Session cleanup requested for sessions older than {max_age_hours} hours")
            # Implementation would check timestamps and remove old sessions
        except Exception as e:
            self.logger.error(f"Error cleaning expired sessions: {e}")
    
    def health_check(self) -> tuple[bool, str]:
        """Check session state manager health"""
        try:
            # Test basic operations
            test_session = "test_health_check"
            self.initialize_session_state(test_session)
            state = self.get_session_state(test_session)
            self.reset_session_state(test_session)
            
            if isinstance(state, dict):
                return True, "Session state manager is healthy"
            else:
                return False, "Session state manager failed basic operations"
        except Exception as e:
            return False, f"Session state manager health check failed: {e}"
