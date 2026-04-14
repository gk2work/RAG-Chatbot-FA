"""
Telegram Webhook Handler
Processes incoming messages and button clicks from Telegram
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.integrations.common.session_manager import BotSessionManager
from app.integrations.common.message_formatter import MessageFormatter
from app.integrations.telegram.button_builder import TelegramButtonBuilder
from app.models.chat import ChatSession
from app.config import Config

# Import your existing RAG service
try:
    from app.services.enhanced_rag import EnhancedRAGService
    ENHANCED_RAG_AVAILABLE = True
    rag_service = EnhancedRAGService()
except ImportError:
    ENHANCED_RAG_AVAILABLE = False
    from app.services.simple_rag_service import SimpleRAGService
    rag_service = SimpleRAGService()

logger = logging.getLogger(__name__)


class TelegramWebhookHandler:
    """Handle incoming Telegram webhooks"""
    
    def __init__(self):
        self.session_manager = BotSessionManager()
        self.message_formatter = MessageFormatter()
        self.button_builder = TelegramButtonBuilder()
        self.rag_service = rag_service
        
    def process_update(self, update_data: Dict) -> Dict[str, Any]:
        """
        Main entry point for processing Telegram updates
        
        Args:
            update_data: Raw webhook data from Telegram
            
        Returns:
            Dict with response data to send back
        """
        try:
            logger.info(f"Processing Telegram update: {update_data.get('update_id')}")
            
            # Handle different update types
            if 'message' in update_data:
                return self._handle_message(update_data['message'])
            elif 'callback_query' in update_data:
                return self._handle_callback_query(update_data['callback_query'])
            else:
                logger.warning(f"Unknown update type: {update_data.keys()}")
                return {'success': False, 'error': 'Unknown update type'}
                
        except Exception as e:
            logger.error(f"Error processing Telegram update: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _handle_message(self, message_data: Dict) -> Dict[str, Any]:
        """Handle incoming text messages"""
        try:
            # Extract message details
            chat_id = message_data['chat']['id']
            user_id = message_data['from']['id']
            message_text = message_data.get('text', '')
            user_metadata = {
                'username': message_data['from'].get('username'),
                'first_name': message_data['from'].get('first_name'),
                'last_name': message_data['from'].get('last_name')
            }
            
            logger.info(f"Message from user {user_id}: {message_text[:50]}...")
            
            # Handle commands
            if message_text.startswith('/'):
                return self._handle_command(chat_id, user_id, message_text, user_metadata)
            
            # Handle regular messages
            return self._handle_regular_message(chat_id, user_id, message_text, user_metadata)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            return self._create_error_response(message_data['chat']['id'])
    
    def _handle_command(self, chat_id: int, user_id: int, command: str, user_metadata: Dict) -> Dict[str, Any]:
        """Handle bot commands like /start, /help"""
        try:
            # Extract command and parameters
            parts = command.split()
            cmd = parts[0].lower()
            params = parts[1:] if len(parts) > 1 else []
            
            if cmd == '/start':
                return self._handle_start_command(chat_id, user_id, params, user_metadata)
            elif cmd == '/help':
                return self._handle_help_command(chat_id)
            elif cmd == '/programs':
                return self._handle_programs_command(chat_id, user_id, user_metadata)
            elif cmd == '/status':
                return self._handle_status_command(chat_id, user_id, user_metadata)
            else:
                return {
                    'chat_id': chat_id,
                    'text': f"Unknown command: {cmd}\n\nUse /help to see available commands.",
                    'success': True
                }
                
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            return self._create_error_response(chat_id)
    
    def _handle_start_command(self, chat_id: int, user_id: int, params: list, user_metadata: Dict) -> Dict[str, Any]:
        """Handle /start command - Initialize conversation"""
        try:
            # Extract university X-ID from deep link (if provided)
            # Example: /start XNR35QWNP
            university_x_id = params[0] if params else Config.DEFAULT_UNIVERSITY_X_ID
            
            # Get or create session
            session_id, is_new = self.session_manager.get_or_create_session(
                platform='telegram',
                user_identifier=str(user_id),
                university_x_id=university_x_id,
                user_metadata=user_metadata
            )
            
            # Get university info directly from database
            from app.models import get_db
            db = get_db()
            universities_collection = db['universities']
            university = universities_collection.find_one({'x_id': university_x_id})
            
            university_name = university.get('name', 'our university') if university else 'our university'
            
            # Get user's first name for personalization
            first_name = user_metadata.get('first_name', 'there')
            
            # Create welcome message
            welcome_text = f"""👋 Welcome to {university_name}, {first_name}!

I'm your AI admission assistant. I can help you with:

🎓 Program information
💰 Fees and scholarships
📝 Admission requirements
🏫 Campus facilities
📅 Application deadlines

What would you like to know today?"""
            
            # Add interactive buttons
            buttons = self.button_builder.create_program_selection_buttons()
            
            # Store welcome message in session
            ChatSession.add_message(session_id, "assistant", welcome_text, {
                'type': 'welcome',
                'is_new_session': is_new,
                'buttons_shown': True
            })
            
            return {
                'chat_id': chat_id,
                'text': welcome_text,
                'reply_markup': buttons,
                'session_id': session_id,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error in start command: {e}", exc_info=True)
            return self._create_error_response(chat_id)
    
    def _handle_help_command(self, chat_id: int) -> Dict[str, Any]:
        """Handle /help command"""
        help_text = """🤖 **Available Commands:**

/start - Start or restart conversation
/help - Show this help message
/programs - Browse available programs
/status - Check your application status

💬 **How to use:**
Just type your question and I'll help you! You can ask about:
- Programs and courses
- Admission requirements
- Fees and scholarships
- Campus facilities
- Application process

I'm here to help 24/7! 😊"""
        
        return {
            'chat_id': chat_id,
            'text': help_text,
            'parse_mode': 'Markdown',
            'success': True
        }
    
    def _handle_programs_command(self, chat_id: int, user_id: int, user_metadata: Dict) -> Dict[str, Any]:
        """Handle /programs command - Show program exploration"""
        try:
            # Get or create session
            session_id, _ = self.session_manager.get_or_create_session(
                platform='telegram',
                user_identifier=str(user_id),
                university_x_id=Config.DEFAULT_UNIVERSITY_X_ID,
                user_metadata=user_metadata
            )
            
            text = """🎓 **Program Exploration**

To help you find the perfect program, I need to know a bit about your background.

What's your highest education level?"""
            
            buttons = self.button_builder.create_education_level_buttons()
            
            return {
                'chat_id': chat_id,
                'text': text,
                'reply_markup': buttons,
                'parse_mode': 'Markdown',
                'session_id': session_id,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error in programs command: {e}")
            return self._create_error_response(chat_id)
    
    def _handle_status_command(self, chat_id: int, user_id: int, user_metadata: Dict) -> Dict[str, Any]:
        """Handle /status command - Check application status"""
        text = """📊 **Application Status**

To check your application status, I need your application ID or the email you used during application.

Please provide one of:
- Application ID (e.g., APP2025-1234)
- Email address"""
        
        return {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown',
            'success': True
        }
    
    def _handle_regular_message(self, chat_id: int, user_id: int, message_text: str, user_metadata: Dict) -> Dict[str, Any]:
        """Handle regular conversational messages"""
        try:
            # Get or create session
            session_id, is_new = self.session_manager.get_or_create_session(
                platform='telegram',
                user_identifier=str(user_id),
                university_x_id=Config.DEFAULT_UNIVERSITY_X_ID,
                user_metadata=user_metadata
            )
            
            # Get session details
            session = self.session_manager.get_session(session_id)
            university_code = session.get('university_code')
            university_x_id = session.get('university_x_id')
            lead_id = session.get('lead_id')
            
            # Store user message
            ChatSession.add_message(session_id, "user", message_text, {
                'platform': 'telegram',
                'user_id': user_id,
                'timestamp': datetime.utcnow()
            })
            
            # Process with RAG service (REUSING YOUR EXISTING SYSTEM!)
            logger.info(f"Processing message with RAG for session {session_id}")
            
            if ENHANCED_RAG_AVAILABLE:
                rag_result = self.rag_service.query(
                    question=message_text,
                    university_code=university_code,
                    university_x_id=university_x_id,
                    session_id=session_id,
                    lead_id=lead_id
                )
            else:
                rag_result = self.rag_service.query(
                    question=message_text,
                    university_code=university_code,
                    session_id=session_id
                )
            
            response_text = rag_result.get('answer', "I'm sorry, I couldn't process that question.")
            metadata = rag_result.get('metadata', {})
            
            # Check if lead was created/updated
            extracted_lead_id = metadata.get('lead_id')
            if extracted_lead_id and extracted_lead_id != lead_id:
                self.session_manager.link_lead_to_session(session_id, extracted_lead_id)
                logger.info(f"Lead {extracted_lead_id} linked to session {session_id}")
            
            # Store assistant response
            ChatSession.add_message(session_id, "assistant", response_text, {
                'platform': 'telegram',
                'rag_metadata': metadata,
                'timestamp': datetime.utcnow()
            })
            
            # Format response for Telegram
            formatted_text = self.message_formatter.format_for_telegram(response_text)
            
            # Check if we should add action buttons
            # (e.g., after providing detailed info, offer next steps)
            buttons = None
            if self._should_add_action_buttons(message_text, response_text, metadata):
                buttons = self.button_builder.create_action_buttons()
            
            return {
                'chat_id': chat_id,
                'text': formatted_text,
                'reply_markup': buttons,
                'session_id': session_id,
                'lead_id': extracted_lead_id,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error handling regular message: {e}", exc_info=True)
            return self._create_error_response(chat_id)
    
    def _handle_callback_query(self, callback_data: Dict) -> Dict[str, Any]:
        """Handle button clicks (callback queries)"""
        try:
            query_id = callback_data['id']
            chat_id = callback_data['message']['chat']['id']
            user_id = callback_data['from']['id']
            data = callback_data.get('data', '')
            
            logger.info(f"Button clicked by user {user_id}: {data}")
            
            # Parse button data
            parsed = self.button_builder.parse_callback_data(data)
            action = parsed['action']
            value = parsed['value']
            
            # Get session
            user_metadata = {
                'username': callback_data['from'].get('username'),
                'first_name': callback_data['from'].get('first_name'),
                'last_name': callback_data['from'].get('last_name')
            }
            
            session_id, _ = self.session_manager.get_or_create_session(
                platform='telegram',
                user_identifier=str(user_id),
                university_x_id=Config.DEFAULT_UNIVERSITY_X_ID,
                user_metadata=user_metadata
            )
            
            # Route based on action
            if action == 'explore_programs':
                response = self._handle_explore_programs(chat_id, session_id)
            elif action == 'fees_scholarships':
                response = self._handle_fees_inquiry(chat_id, session_id)
            elif action == 'admission_process':
                response = self._handle_admission_inquiry(chat_id, session_id)
            elif action == 'campus_facilities':
                response = self._handle_campus_inquiry(chat_id, session_id)
            elif action == 'ask_question':
                response = self._handle_open_question(chat_id)
            elif action == 'education_level':
                response = self._handle_education_level_selection(chat_id, session_id, value)
            elif action == 'field_of_study':
                response = self._handle_field_selection(chat_id, session_id, value)
            elif action == 'talk_to_counselor':
                response = self._handle_counselor_request(chat_id, session_id)
            elif action == 'start_application':
                response = self._handle_application_start(chat_id, session_id)
            elif action == 'more_questions':
                response = self._handle_open_question(chat_id)
            else:
                response = {
                    'chat_id': chat_id,
                    'text': f"Processing: {action}...",
                    'success': True
                }
            
            # Add callback answer (acknowledges button click)
            response['callback_query_id'] = query_id
            response['callback_answer'] = "✓"
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling callback query: {e}", exc_info=True)
            return {
                'callback_query_id': callback_data.get('id'),
                'callback_answer': "Error processing request",
                'success': False
            }
    
    def _handle_explore_programs(self, chat_id: int, session_id: str) -> Dict[str, Any]:
        """Handle 'Explore Programs' button click"""
        text = """🎓 **Let's find the perfect program for you!**

What's your highest education level?"""
        
        buttons = self.button_builder.create_education_level_buttons()
        
        return {
            'chat_id': chat_id,
            'text': text,
            'reply_markup': buttons,
            'parse_mode': 'Markdown',
            'success': True
        }
    
    def _handle_fees_inquiry(self, chat_id: int, session_id: str) -> Dict[str, Any]:
        """Handle fees inquiry with RAG"""
        # Use RAG to answer
        session = self.session_manager.get_session(session_id)
        
        rag_result = self.rag_service.query(
            question="What are the tuition fees and scholarship options?",
            university_code=session.get('university_code'),
            university_x_id=session.get('university_x_id'),
            session_id=session_id
        )
        
        return {
            'chat_id': chat_id,
            'text': rag_result.get('answer', 'I can help you with fees information. Please specify which program you\'re interested in.'),
            'success': True
        }
    
    def _handle_admission_inquiry(self, chat_id: int, session_id: str) -> Dict[str, Any]:
        """Handle admission process inquiry"""
        session = self.session_manager.get_session(session_id)
        
        rag_result = self.rag_service.query(
            question="What is the admission process and requirements?",
            university_code=session.get('university_code'),
            university_x_id=session.get('university_x_id'),
            session_id=session_id
        )
        
        return {
            'chat_id': chat_id,
            'text': rag_result.get('answer'),
            'success': True
        }
    
    def _handle_campus_inquiry(self, chat_id: int, session_id: str) -> Dict[str, Any]:
        """Handle campus facilities inquiry"""
        session = self.session_manager.get_session(session_id)
        
        rag_result = self.rag_service.query(
            question="Tell me about the campus facilities and student life",
            university_code=session.get('university_code'),
            university_x_id=session.get('university_x_id'),
            session_id=session_id
        )
        
        return {
            'chat_id': chat_id,
            'text': rag_result.get('answer'),
            'success': True
        }
    
    def _handle_open_question(self, chat_id: int) -> Dict[str, Any]:
        """Handle 'Ask Question' mode"""
        text = """💬 **Ask me anything!**

Feel free to type your question about:
- Programs and courses
- Admission requirements
- Fees and scholarships
- Campus life
- Application process

I'm here to help! 😊"""
        
        return {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown',
            'success': True
        }
    
    def _handle_education_level_selection(self, chat_id: int, session_id: str, level: str) -> Dict[str, Any]:
        """Handle education level selection"""
        # Store selection in session (you can enhance this later)
        level_map = {
            'high_school': "12th Pass / High School",
            'bachelors': "Bachelor's Degree",
            'masters': "Master's Degree",
            'phd': "PhD / Research"
        }
        
        selected_level = level_map.get(level, level)
        
        text = f"""Great! You have: **{selected_level}**

What field did you study?"""
        
        buttons = self.button_builder.create_field_of_study_buttons()
        
        return {
            'chat_id': chat_id,
            'text': text,
            'reply_markup': buttons,
            'parse_mode': 'Markdown',
            'success': True
        }
    
    def _handle_field_selection(self, chat_id: int, session_id: str, field: str) -> Dict[str, Any]:
        """Handle field of study selection and show recommendations"""
        field_map = {
            'engineering': "Engineering/Tech",
            'business': "Business/Commerce",
            'science': "Science",
            'arts': "Arts/Humanities",
            'medical': "Medical/Health"
        }
        
        selected_field = field_map.get(field, field)
        
        # Use RAG to get program recommendations
        session = self.session_manager.get_session(session_id)
        
        rag_result = self.rag_service.query(
            question=f"What programs do you recommend for someone with a background in {selected_field}?",
            university_code=session.get('university_code'),
            university_x_id=session.get('university_x_id'),
            session_id=session_id
        )
        
        response_text = f"Based on your **{selected_field}** background:\n\n{rag_result.get('answer')}"
        
        buttons = self.button_builder.create_action_buttons()
        
        return {
            'chat_id': chat_id,
            'text': response_text,
            'reply_markup': buttons,
            'parse_mode': 'Markdown',
            'success': True
        }
    
    def _handle_counselor_request(self, chat_id: int, session_id: str) -> Dict[str, Any]:
        """Handle request to talk to counselor"""
        text = """📞 **Connect with Admission Counselor**

I'd be happy to connect you with our admission counselor!

Please share your email address and we'll have them reach out to you within 24 hours."""
        
        return {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown',
            'success': True
        }
    
    def _handle_application_start(self, chat_id: int, session_id: str) -> Dict[str, Any]:
        """Handle application start"""
        session = self.session_manager.get_session(session_id)
        university_x_id = session.get('university_x_id')
        
        # Get university application link
        from app.models.university import University
        university = University.get_by_x_id(university_x_id)
        
        text = """📝 **Start Your Application**

Great! I'm excited to help you begin your application.

To get started, please provide your:
1. Full Name
2. Email Address
3. Phone Number

Or you can directly visit our application portal: """
        
        if university and university.get('contact_info', {}).get('website_url'):
            text += f"\n🔗 {university['contact_info']['website_url']}/apply"
        
        return {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown',
            'success': True
        }
    
    def _should_add_action_buttons(self, user_message: str, response: str, metadata: Dict) -> bool:
        """Determine if action buttons should be shown"""
        # Add buttons if:
        # 1. Response is detailed (> 200 chars)
        # 2. User asked about programs, fees, or admission
        # 3. Lead information was extracted
        
        if len(response) > 200:
            return True
        
        keywords = ['program', 'course', 'fee', 'admission', 'apply', 'scholarship']
        if any(keyword in user_message.lower() for keyword in keywords):
            return True
        
        if metadata.get('lead_created') or metadata.get('lead_updated'):
            return True
        
        return False
    
    def _create_error_response(self, chat_id: int) -> Dict[str, Any]:
        """Create generic error response"""
        return {
            'chat_id': chat_id,
            'text': "I'm sorry, I encountered an error processing your request. Please try again or use /help for assistance.",
            'success': False
        }