"""
Telegram Button Builder
Creates interactive buttons, inline keyboards, and quick replies
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class TelegramButtonBuilder:
    """Build interactive buttons for Telegram"""
    
    @staticmethod
    def create_inline_keyboard(buttons: List[Dict[str, str]]) -> Dict:
        """
        Create inline keyboard (buttons below message)
        
        Args:
            buttons: List of dicts with 'text' and 'callback_data'
            Example: [
                {'text': '🎓 Explore Programs', 'callback_data': 'explore_programs'},
                {'text': '💰 Fees & Scholarships', 'callback_data': 'fees_scholarships'}
            ]
        
        Returns:
            Telegram inline_keyboard dict
        """
        if not buttons:
            return None
        
        try:
            # Create rows of buttons (max 2 buttons per row for better UX)
            keyboard = []
            row = []
            
            for i, button in enumerate(buttons):
                row.append({
                    'text': button.get('text', 'Option'),
                    'callback_data': button.get('callback_data', f'button_{i}')
                })
                
                # Add row after 2 buttons or at the end
                if len(row) == 2 or i == len(buttons) - 1:
                    keyboard.append(row)
                    row = []
            
            return {
                'inline_keyboard': keyboard
            }
            
        except Exception as e:
            logger.error(f"Error creating inline keyboard: {e}")
            return None
    
    @staticmethod
    def create_program_selection_buttons() -> Dict:
        """Create buttons for program exploration"""
        buttons = [
            {'text': '🎓 Explore Programs', 'callback_data': 'explore_programs'},
            {'text': '💰 Fees & Scholarships', 'callback_data': 'fees_scholarships'},
            {'text': '📝 Admission Process', 'callback_data': 'admission_process'},
            {'text': '🏫 Campus & Facilities', 'callback_data': 'campus_facilities'},
            {'text': '💬 Ask Specific Question', 'callback_data': 'ask_question'}
        ]
        return TelegramButtonBuilder.create_inline_keyboard(buttons)
    
    @staticmethod
    def create_education_level_buttons() -> Dict:
        """Create buttons for education level selection"""
        buttons = [
            {'text': '🎓 12th Pass / High School', 'callback_data': 'edu_high_school'},
            {'text': '📘 Bachelor\'s Degree', 'callback_data': 'edu_bachelors'},
            {'text': '📗 Master\'s Degree', 'callback_data': 'edu_masters'},
            {'text': '🔬 PhD / Research', 'callback_data': 'edu_phd'}
        ]
        return TelegramButtonBuilder.create_inline_keyboard(buttons)
    
    @staticmethod
    def create_field_of_study_buttons() -> Dict:
        """Create buttons for field of study selection"""
        buttons = [
            {'text': '💻 Engineering/Tech', 'callback_data': 'field_engineering'},
            {'text': '📊 Business/Commerce', 'callback_data': 'field_business'},
            {'text': '🔬 Science', 'callback_data': 'field_science'},
            {'text': '🎨 Arts/Humanities', 'callback_data': 'field_arts'},
            {'text': '⚕️ Medical/Health', 'callback_data': 'field_medical'},
            {'text': '✍️ Other', 'callback_data': 'field_other'}
        ]
        return TelegramButtonBuilder.create_inline_keyboard(buttons)
    
    @staticmethod
    def create_yes_no_buttons(yes_callback: str = 'yes', no_callback: str = 'no') -> Dict:
        """Create simple Yes/No buttons"""
        buttons = [
            {'text': '✅ Yes', 'callback_data': yes_callback},
            {'text': '❌ No', 'callback_data': no_callback}
        ]
        return TelegramButtonBuilder.create_inline_keyboard(buttons)
    
    @staticmethod
    def create_action_buttons() -> Dict:
        """Create action buttons for after providing information"""
        buttons = [
            {'text': '📞 Talk to Counselor', 'callback_data': 'talk_counselor'},
            {'text': '📝 Start Application', 'callback_data': 'start_application'},
            {'text': '💬 More Questions', 'callback_data': 'more_questions'}
        ]
        return TelegramButtonBuilder.create_inline_keyboard(buttons)
    
    @staticmethod
    def parse_callback_data(callback_data: str) -> Dict[str, Any]:
        """
        Parse callback data from button clicks
        
        Args:
            callback_data: String like 'explore_programs' or 'edu_bachelors'
        
        Returns:
            Dict with parsed action and data
        """
        try:
            parts = callback_data.split('_')
            
            # Map callback patterns to actions
            action_map = {
                'explore': 'explore_programs',
                'fees': 'fees_scholarships',
                'admission': 'admission_process',
                'campus': 'campus_facilities',
                'ask': 'ask_question',
                'edu': 'education_level',
                'field': 'field_of_study',
                'yes': 'confirm_yes',
                'no': 'confirm_no',
                'talk': 'talk_to_counselor',
                'start': 'start_application',
                'more': 'more_questions'
            }
            
            action = parts[0]
            value = '_'.join(parts[1:]) if len(parts) > 1 else None
            
            return {
                'action': action_map.get(action, callback_data),
                'value': value,
                'raw': callback_data
            }
            
        except Exception as e:
            logger.error(f"Error parsing callback data: {e}")
            return {
                'action': 'unknown',
                'value': None,
                'raw': callback_data
            }