"""
Dynamic questioner for Enhanced RAG Service
"""

import logging
import random
import re
from typing import Dict, List, Any, Optional
from app.models.university import University
from ..base.interfaces import QuestioningInterface
from .sequence_manager import SequenceManager


class DynamicQuestioner(QuestioningInterface):
    """Handles dynamic question generation and management"""
    
    def __init__(self, sequence_manager: SequenceManager):
        super().__init__()
        self.sequence_manager = sequence_manager
        
        # Dynamic questions for different categories
        self.dynamic_questions = {
            "user_name": [
                "What's your name, so I can personalize my assistance for you?",
                "May I know your name to better help you with your inquiries?",
                "What name would you like me to use while we discuss your educational interests?",
                "Could you tell me your name so I can address you properly?",
                "What should I call you as we explore your academic options?"
            ],
            "user_email": [
                "Could you share your email address so I can provide you with detailed program information?",
                "What's the best email address to reach you at?",
                "If you'd like, I can share detailed brochures with you. What's your email?",
                "May I have your email to send you comprehensive program details?",
                "Could you provide your email for any follow-up information?"
            ],
            "user_country": [
                "Which country are you from? This helps me provide relevant admission guidance.",
                "Where would you be applying from? Different regions have different requirements.",
                "Could you tell me your country? This helps with specific admission procedures.",
                "Which country are you based in? This affects program availability and requirements.",
                "Where are you located? This helps me give you region-specific information."
            ],
            "educational_background": [
                "Could you tell me about your educational background?",
                "What's your current or most recent educational qualification?",
                "What degree have you completed or are you currently pursuing?",
                "May I know about your academic background to suggest suitable programs?",
                "What's your educational foundation? This helps me recommend the right programs."
            ],
            "academic_interests": [
                "What field of study interests you most?",
                "Are there any specific programs you'd like to learn about?",
                "What's your area of academic interest?"
            ],
            "career_goals": [
                "What are your career aspirations after graduation?",
                "Do you have specific career goals in mind?",
                "What kind of career path are you considering?"
            ]
        }
    
    def get_dynamic_question(self, conversation_context: Dict, question: str, 
                           university_x_id: str = None) -> Optional[str]:
        """Get dynamic question based on conversation state with sequential ordering"""
        try:
            if not self.sequence_manager.get_questioning_config().get("enable_dynamic_questioning", True):
                return None
            
            # Get user info from context
            user_info = conversation_context.get('user_info', {})
            conversation_length = conversation_context.get('conversation_length', 0)
            session_id = conversation_context.get('session_id')
            
            # Initialize session state if needed
            session_state = conversation_context.get('session_state', {})
            if not session_state:
                session_state = {
                    "questions_asked": [],
                    "last_question_turn": 0,
                    "failed_attempts": {},
                    "phase": 1
                }
            
            # Check if we should ask a question
            if not self.sequence_manager.should_ask_question(conversation_length, session_state):
                return None
            
            # Find the next question category based on sequential order
            next_question_category = self.sequence_manager.get_next_question_category(
                user_info, session_state, conversation_length
            )
            
            if next_question_category:
                questions_list = self.dynamic_questions.get(next_question_category, [])
                if questions_list:
                    selected_question = random.choice(questions_list)
                    
                    # Update session state
                    session_state["questions_asked"].append(next_question_category)
                    session_state["last_question_turn"] = conversation_length
                    
                    self.logger.debug(f"Dynamic question selected: {next_question_category}")
                    return selected_question
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in dynamic questioning: {e}")
            return None
    
    def is_response_to_dynamic_question(self, conversation_context: Dict) -> bool:
        """Check if the current message is a response to a recent dynamic question"""
        try:
            recent_messages = conversation_context.get('message_history', [])[-5:]
            
            for msg in reversed(recent_messages):
                if msg.get('role') == 'assistant':
                    content = msg.get('content', '').lower()
                    
                    # Look for question indicators in recent assistant messages
                    question_indicators = [
                        'what\'s your name',
                        'may i know your name',
                        'what\'s your email',
                        'email address',
                        'which country',
                        'where are you from',
                        'educational background',
                        'what degree do you',
                        'could you tell me your name',
                        'could you share your name',
                        'what name would you like me to use',
                        'so i can address you properly',
                        'could you share your email',
                        'what\'s the best email',
                        'if you\'d like, i can share',
                        'could you tell me your country',
                        'which country are you',
                        'where would you be applying from',
                        'could you tell me about your educational',
                        'what\'s your current or most recent',
                        'what field of study interests',
                        'what are your career aspirations'
                    ]
                    
                    if any(indicator in content for indicator in question_indicators):
                        self.logger.debug(f"Found recent dynamic question: {content[:100]}...")
                        return True
                        
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking for dynamic question response: {e}")
            return False
    
    def get_next_sequential_question(self, user_info: Dict, session_state: Dict, conversation_length: int) -> Optional[Dict]:
        """Get next sequential question - delegated to sequence manager"""
        return self.sequence_manager.find_next_sequential_question(user_info, session_state, conversation_length)
    
    def generate_dynamic_response_acknowledgment(self, question: str, conversation_context: Dict, 
                                               university_x_id: str) -> Dict[str, Any]:
        """Generate a brief acknowledgment for simple dynamic question responses"""
        try:
            # Get university info for personalization
            university = University.get_university_by_x_id(university_x_id) if university_x_id else None
            university_name = university.get('name', 'our university') if university else 'our university'
            
            # Get user info from conversation context
            user_info = conversation_context.get('user_info', {})
            user_name = user_info.get('name', '')
            
            # Determine what type of response this was
            recent_messages = conversation_context.get('message_history', [])[-3:]
            response_type = "general"
            
            for msg in reversed(recent_messages):
                if msg.get('role') == 'assistant':
                    assistant_msg = msg.get('content', '').lower()
                    if any(name_q in assistant_msg for name_q in ['name', 'call you']):
                        response_type = "name"
                        break
                    elif 'email' in assistant_msg:
                        response_type = "email"
                        break
                    elif any(country_q in assistant_msg for country_q in ['country', 'from', 'where']):
                        response_type = "country"
                        break
                    elif 'educational' in assistant_msg or 'background' in assistant_msg:
                        response_type = "education"
                        break
            
            # Generate appropriate acknowledgment based on response type
            if response_type == "name" and user_name:
                acknowledgments = [
                    f"Nice to meet you, {user_name}! 😊",
                    f"Great to meet you, {user_name}!",
                    f"Hello {user_name}! Pleasure to meet you.",
                    f"Hi {user_name}! It's wonderful to meet you.",
                    f"Thank you, {user_name}! Great to connect with you."
                ]
            elif response_type == "email":
                acknowledgments = [
                    "Perfect! I've noted your email address. 📧",
                    "Thank you for sharing your email! That's helpful.",
                    "Got it! Your email has been saved.",
                    "Excellent! I've recorded your email address."
                ]
            elif response_type == "country":
                acknowledgments = [
                    "Thank you for letting me know! 🌍",
                    "Got it! That helps me provide more relevant information.",
                    "Perfect! I can now tailor my guidance for your location.",
                    "Thank you for sharing! That's very helpful to know."
                ]
            else:
                acknowledgments = [
                    "Thank you for sharing that information! 👍",
                    "Got it! That's helpful to know.",
                    "Perfect! Thank you for letting me know.",
                    "Great! I've noted that information."
                ]
            
            # Select a random acknowledgment
            acknowledgment = random.choice(acknowledgments)
            
            # Add a follow-up to continue the conversation
            follow_ups = [
                f"How can I help you learn more about {university_name} today?",
                f"What would you like to know about {university_name}?",
                f"What information about {university_name} would be most helpful for you?",
                f"Is there anything specific about {university_name} you'd like to explore?",
                f"What aspects of {university_name} interest you most?"
            ]
            
            follow_up = random.choice(follow_ups)
            
            # Combine acknowledgment with follow-up
            response_text = f"{acknowledgment}\n\n{follow_up}"
            
            return {
                "answer": response_text,
                "response_type": "dynamic_acknowledgment",
                "acknowledgment_type": response_type,
                "conversation_aware": True,
                "university_branded": True,
                "user_name": user_name
            }
            
        except Exception as e:
            self.logger.error(f"Error generating dynamic acknowledgment: {e}")
            # Fallback response
            return {
                "answer": "Thank you for sharing that! How can I help you learn more about our programs today?",
                "response_type": "dynamic_acknowledgment_fallback"
            }
    
    def is_simple_dynamic_response(self, question: str, conversation_context: Dict, lead_extracted: bool) -> bool:
        """Check if this is a simple response to a recent dynamic question"""
        try:
            # If no lead was extracted, it's probably not a simple info response
            if not lead_extracted:
                return False
            
            # Check if this appears to be a response to a dynamic question
            if not self.is_response_to_dynamic_question(conversation_context):
                return False
            
            # Check if the response is relatively simple (not a complex query)
            question_words = len(question.strip().split())
            if question_words > 15:  # If more than 15 words, probably not a simple response
                return False
            
            # Check if it contains typical question words (indicates it's not just a simple answer)
            question_indicators = ['what', 'how', 'when', 'where', 'why', 'which', 'can', 'could', 'would', 'should', 'tell me about']
            question_lower = question.lower()
            
            if any(indicator in question_lower for indicator in question_indicators):
                return False  # This looks like a question, not a simple response
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking for simple dynamic response: {e}")
            return False
    
    def health_check(self) -> tuple[bool, str]:
        """Check dynamic questioner health"""
        try:
            # Test basic functionality
            test_context = {
                'user_info': {},
                'conversation_length': 1,
                'session_state': {"questions_asked": [], "failed_attempts": {}, "last_question_turn": 0, "phase": 1}
            }
            try:
                question = self.get_dynamic_question(test_context, "hello")
                # Should return a question for user_name since it's the first required question
                if question and any(name_indicator in question.lower() for name_indicator in ['name', 'call']):
                    return True, "Dynamic questioner is healthy"
                else:
                    return True, "Dynamic questioner is working but no question generated (normal)"
            except Exception as e:
                return False, f"Dynamic questioner failed: {e}"
        except Exception as e:
            return False, f"Dynamic questioner health check failed: {e}"
