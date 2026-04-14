"""
Sequential questioning manager for Enhanced RAG Service
"""

import logging
import re
from typing import Dict, List, Any, Optional
from ..base.interfaces import BaseRAGComponent


class SequenceManager(BaseRAGComponent):
    """Manages sequential questioning logic and state tracking"""
    
    def __init__(self):
        super().__init__()
        
        # Sequential questioning configuration
        self.question_sequence = [
            {"category": "user_name", "priority": 1, "required": True, "conversation_turn": 1},
            {"category": "educational_background", "priority": 2, "required": True, "conversation_turn": 2},
            {"category": "user_email", "priority": 3, "required": True, "conversation_turn": 4},
            {"category": "user_country", "priority": 4, "required": True, "conversation_turn": 6},
            {"category": "academic_interests", "priority": 5, "required": False, "conversation_turn": 8},
            {"category": "career_goals", "priority": 6, "required": False, "conversation_turn": 10}
        ]
        
        # Questioning configuration
        self.questioning_config = {
            "max_failed_attempts": 2,
            "question_cooldown_turns": 2,
            "enable_dynamic_questioning": True,
            "ask_questions_every_n_turns": 2,
            "max_questions_per_conversation": 7
        }
    
    def find_next_sequential_question(self, user_info: Dict, session_state: Dict, conversation_length: int) -> Optional[Dict]:
        """Find the next question to ask based on the sequential order and current state"""
        questions_asked = set(session_state.get("questions_asked", []))
        failed_attempts = session_state.get("failed_attempts", {})
        
        # Go through the sequence in order
        for question_config in self.question_sequence:
            category = question_config["category"]
            
            # Skip if already asked
            if category in questions_asked:
                continue
            
            # Skip if too many failed attempts
            if failed_attempts.get(category, 0) >= self.questioning_config["max_failed_attempts"]:
                continue
            
            # Check if we have the required information already
            if category == "user_name" and user_info.get("name"):
                continue
            elif category == "user_email" and user_info.get("email"):
                email = user_info.get("email", "")
                if email and not email.startswith("temp_") and "@placeholder.com" not in email:
                    continue
            elif category == "user_country" and user_info.get("country") and user_info.get("country") != "Unknown":
                continue
            
            # Check if it's the right time to ask this question
            min_turn = question_config.get("conversation_turn", 1)
            if conversation_length >= min_turn:
                return question_config
            
            # For required questions, ask them even if it's early (but not on first message)
            if question_config.get("required", False) and conversation_length > 0:
                return question_config
        
        return None
    
    def get_next_question_category(self, user_info: Dict, session_state: Dict, conversation_length: int) -> Optional[str]:
        """Determine the next question category to ask based on sequential order"""
        questions_asked = set(session_state.get("questions_asked", []))
        failed_attempts = session_state.get("failed_attempts", {})
        
        self.logger.debug(f"🔍 Question category check - Asked: {questions_asked}, User: {user_info}")
        
        # Phase 1: REQUIRED personal information - CORRECT ORDER: Name → Email → Other
        
        # 1. FIRST: Always ask for name if not available (MOST IMPORTANT)
        if "user_name" not in questions_asked and not user_info.get('name'):
            if conversation_length >= 1:  # Ask from turn 1
                self.logger.debug("✅ Next question: user_name")
                return "user_name"
        
        # 2. SECOND: Ask for email after name (REQUIRED BEFORE OTHER INFO)
        if ("user_email" not in questions_asked and 
            user_info.get('name') and  # Have name first
            conversation_length >= 2):  # Ask from turn 2
            
            # Check if we have a real email (not placeholder)
            email = user_info.get('email', '')
            if not email or email.startswith('temp_') or '@placeholder.com' in email:
                self.logger.debug("✅ Next question: user_email")
                return "user_email"
        
        # 3. THIRD: Ask for educational background after email
        if ("educational_background" not in questions_asked and 
            user_info.get('name') and  # Have name
            user_info.get('email') and not user_info.get('email', '').endswith('@placeholder.com') and  # Have real email
            conversation_length >= 4):  # Ask from turn 4
            self.logger.debug("✅ Next question: educational_background")
            return "educational_background"
        
        # 4. FOURTH: Ask for country after email and educational background
        if ("user_country" not in questions_asked and 
            user_info.get('name') and  # Have name
            user_info.get('email') and not user_info.get('email', '').endswith('@placeholder.com') and  # Have real email
            conversation_length >= 6):  # Ask from turn 6
            
            # Check if we have real country info
            country = user_info.get('country', '')
            if not country or country == 'Unknown':
                self.logger.debug("✅ Next question: user_country")
                return "user_country"
        
        # Phase 2: OPTIONAL academic and preference information
        
        # 5. Academic interests
        if ("academic_interests" not in questions_asked and 
            user_info.get('name') and user_info.get('email') and user_info.get('country') and
            conversation_length >= 8):
            self.logger.debug("✅ Next question: academic_interests")
            return "academic_interests"
        
        # 6. Career goals
        if ("career_goals" not in questions_asked and 
            user_info.get('name') and user_info.get('email') and user_info.get('country') and
            conversation_length >= 10):
            self.logger.debug("✅ Next question: career_goals")
            return "career_goals"
        
        self.logger.debug("❌ No more questions to ask")
        return None
    
    def update_question_state_on_response(self, session_id: str, session_state: Dict, question_asked: str, user_response: str):
        """Update questioning state when user responds to a question"""
        try:
            question_lower = question_asked.lower()
            response_lower = user_response.lower()
            
            # Check if user provided information for any category
            categories_provided = []
            
            # Check for name
            if any(name_indicator in question_lower for name_indicator in ['name', 'call you']):
                name_patterns = [
                    r'my name is (\w+)',
                    r"i'm (\w+)",
                    r'call me (\w+)',
                    r"i am (\w+)"
                ]
                for pattern in name_patterns:
                    if re.search(pattern, response_lower):
                        categories_provided.append("user_name")
                        break
            
            # Check for email
            if 'email' in question_lower:
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                if re.search(email_pattern, user_response):
                    categories_provided.append("user_email")
            
            # Check for country
            if 'country' in question_lower or 'from' in question_lower:
                # Simple country detection - could be enhanced
                if len(user_response.strip()) > 2 and not any(negative in response_lower for negative in ['no', 'not', 'don\'t']):
                    categories_provided.append("user_country")
            
            # Update session state based on what was provided
            for category in categories_provided:
                if category in session_state.get("questions_asked", []):
                    session_state.setdefault("questions_answered", []).append(category)
                    # Reset failed attempts for this category
                    if category in session_state.get("failed_attempts", {}):
                        del session_state["failed_attempts"][category]
            
            # If no information was provided, increment failed attempts
            if not categories_provided:
                last_question_category = session_state.get("questions_asked", [])[-1] if session_state.get("questions_asked") else None
                if last_question_category:
                    session_state.setdefault("failed_attempts", {})[last_question_category] = \
                        session_state.get("failed_attempts", {}).get(last_question_category, 0) + 1
            
        except Exception as e:
            self.logger.error(f"Error updating question state: {e}")
    
    def should_ask_question(self, conversation_length: int, session_state: Dict, is_first_message: bool = False) -> bool:
        """Check if we should ask a question at this point in the conversation"""
        try:
            # Don't ask questions too frequently - maintain natural conversation flow
            turns_since_last_question = conversation_length - session_state.get("last_question_turn", 0)
            if turns_since_last_question < self.questioning_config["ask_questions_every_n_turns"] and not is_first_message:
                return False
            
            # Check if we've asked enough questions
            total_questions_asked = len(session_state.get("questions_asked", []))
            if total_questions_asked >= self.questioning_config["max_questions_per_conversation"]:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking if should ask question: {e}")
            return False
    
    def get_questioning_config(self) -> Dict[str, Any]:
        """Get questioning configuration"""
        return self.questioning_config.copy()
    
    def get_question_sequence(self) -> List[Dict]:
        """Get question sequence configuration"""
        return self.question_sequence.copy()
    
    def health_check(self) -> tuple[bool, str]:
        """Check sequence manager health"""
        try:
            # Test basic functionality
            test_user_info = {}
            test_session_state = {"questions_asked": [], "failed_attempts": {}}
            test_conversation_length = 1
            
            next_question = self.find_next_sequential_question(test_user_info, test_session_state, test_conversation_length)
            if next_question and next_question.get("category") == "user_name":
                return True, "Sequence manager is healthy"
            else:
                return False, "Sequence manager failed next question test"
        except Exception as e:
            return False, f"Sequence manager health check failed: {e}"
