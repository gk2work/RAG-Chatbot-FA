"""
Lead extraction and management for Enhanced RAG Service
"""

import json
import re
import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple
from openai import OpenAI

from app.config import Config
from app.models.lead import Lead
from ..base.interfaces import LeadManagerInterface


class LeadExtractor(LeadManagerInterface):
    """Handles lead extraction and management from user conversations"""
    
    def __init__(self, openai_client: OpenAI):
        super().__init__()
        self.openai_client = openai_client
        
        # Model configuration
        self.extraction_model = getattr(Config, 'EXTRACTION_MODEL', 'gpt-3.5-turbo')
        self.extraction_max_tokens = 1500
        
        # Statistics tracking
        self.stats = {'leads_created': 0, 'leads_updated': 0}
        
        # Personal info extraction keywords for smart filtering
        self.personal_info_keywords = [
            'name', 'email', 'country', 'from', 'called', 'address', 'phone', 'mobile',
            'nationality', 'location', 'my name is', "i'm", "call me", 'completed', 
            'graduated', 'degree', 'bachelor', 'master', 'btech', 'mtech', 'phd',
            'diploma', 'engineering', 'background', 'studied', 'qualification'
        ]
    
    def extract_and_manage_lead(self, question: str, session_id: str, lead_id: str, 
                               conversation_context: Dict) -> Tuple[bool, Dict[str, Any]]:
        """Extract and manage lead information optimized"""
        try:
            university_code = conversation_context.get('university_code', 'unknown')
            university_x_id = conversation_context.get('university_x_id', None)
            
            # If we already have a lead_id, check if we need to update it
            if lead_id:
                question_lower = question.lower()
                has_personal_keywords = any(keyword in question_lower for keyword in self.personal_info_keywords)
                if not has_personal_keywords:
                    return False, {'lead_id': lead_id}

            # Check if this is a response to a dynamic question for enhanced extraction
            is_dynamic_response = self._is_response_to_dynamic_question(conversation_context)
            
            # Simple pattern matching for names and educational background
            question_lower = question.lower()
            question_trimmed = question.strip()
            
            # Enhanced name patterns - including simple responses for dynamic questions
            simple_name_patterns = [
                r'my name is (\w+)',
                r"i'm (\w+)",
                r'call me (\w+)',
                r"i am (\w+)(?!\s+(from|a|an|in)\s+(btech|b\.tech|bachelor|engineering|computer|mechanical|electrical))"
            ]
            
            # Educational background patterns
            education_patterns = [
                r'completed (b\.?tech|bachelor|btech|be)',
                r'graduated (b\.?tech|bachelor|btech|be)',
                r'have (b\.?tech|bachelor|btech|be)',
                r'did (b\.?tech|bachelor|btech|be)',
                r'(ece|cse|mechanical|electrical|civil|chemical|it|computer) department',
                r'(engineering|technology|science) background'
            ]
            
            extracted_name = None
            extracted_education = None
            extracted_email = None
            extracted_country = None
            
            # Enhanced extraction for dynamic question responses
            if is_dynamic_response:
                # Check if recent question was about name and extract simple name response
                recent_messages = conversation_context.get('message_history', [])[-3:]
                for msg in reversed(recent_messages):
                    if msg.get('role') == 'assistant':
                        assistant_msg = msg.get('content', '').lower()
                        
                        # Name extraction for dynamic questions
                        if any(name_q in assistant_msg for name_q in ['name', 'call you']):
                            # Simple name pattern: just extract the first word if it looks like a name
                            if re.match(r'^[a-zA-Z]+$', question_trimmed) and len(question_trimmed) > 1:
                                extracted_name = question_trimmed.title()
                                self.logger.debug(f"Extracted name from dynamic response: {extracted_name}")
                                break
                        
                        # Email extraction for dynamic questions
                        elif 'email' in assistant_msg:
                            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                            email_match = re.search(email_pattern, question)
                            if email_match:
                                extracted_email = email_match.group(0)
                                self.logger.debug(f"Extracted email from dynamic response: {extracted_email}")
                                break
                        
                        # Country extraction for dynamic questions
                        elif any(country_q in assistant_msg for country_q in ['country', 'from', 'where']):
                            # Simple country extraction: any reasonable length text response
                            if len(question_trimmed) > 2 and not any(neg in question_lower for neg in ['no', 'not', 'don\'t', 'none']):
                                extracted_country = question_trimmed.title()
                                self.logger.debug(f"Extracted country from dynamic response: {extracted_country}")
                                break
            
            # Standard name extraction (fallback or non-dynamic responses)
            if not extracted_name:
                for pattern in simple_name_patterns:
                    match = re.search(pattern, question_lower)
                    if match:
                        extracted_name = match.group(1).title()
                        break
            
            # Standard email extraction (fallback)
            if not extracted_email:
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                email_match = re.search(email_pattern, question)
                if email_match:
                    extracted_email = email_match.group(0)
            
            # Extract educational background
            for pattern in education_patterns:
                match = re.search(pattern, question_lower)
                if match:
                    extracted_education = match.group(0)
                    break

            # Use extraction model for more complex extraction if simple patterns fail
            if (not any([extracted_name, extracted_email, extracted_country, extracted_education])) and any(keyword in question_lower for keyword in self.personal_info_keywords):
                try:
                    extraction_prompt = f"""
                    Extract personal and educational information from this message. Return JSON format only:
                    {{"name": "extracted_name", "email": "extracted_email", "country": "extracted_country", "education": "educational_background"}}
                    If not found, return null for that field.
                    
                    Message: {question}
                    """
                    
                    response = self.openai_client.chat.completions.create(
                        model=self.extraction_model,
                        messages=[{"role": "user", "content": extraction_prompt}],
                        temperature=0.1,
                        max_tokens=self.extraction_max_tokens
                    )
                    
                    result = response.choices[0].message.content
                    extracted_info = json.loads(result)
                    if not extracted_name:
                        extracted_name = extracted_info.get('name')
                    if not extracted_email:
                        extracted_email = extracted_info.get('email')
                    if not extracted_country:
                        extracted_country = extracted_info.get('country')
                    if not extracted_education:
                        extracted_education = extracted_info.get('education')
                    
                except Exception as extraction_error:
                    self.logger.warning(f"Extraction API call failed: {extraction_error}")

            # Create or update lead if we have new information
            if any([extracted_name, extracted_email, extracted_country, extracted_education]):
                try:
                    if not lead_id:
                        # Create new lead with all available information
                        if not extracted_email:
                            placeholder_email = extracted_email or f"temp_{session_id}_{str(uuid.uuid4())[:8]}@placeholder.com"
                        else:
                            placeholder_email = extracted_email
                        lead_id, is_existing = Lead.create_lead(
                            name=extracted_name or "Unknown",
                            email=placeholder_email,
                            university_code=university_code,
                            country=extracted_country or "Unknown",
                            educational_background=extracted_education,
                            university_x_id=university_x_id
                        )
                        
                        if lead_id:
                            Lead.add_chat_session(lead_id, session_id)
                            self.stats['leads_created'] += 1
                            self.logger.info(f"Created new lead with: name={extracted_name}, email={extracted_email}, country={extracted_country}")
                    else:
                        # Update existing lead with new information
                        update_data = {}
                        if extracted_name:
                            update_data['name'] = extracted_name
                        if extracted_email:
                            update_data['email'] = extracted_email
                        if extracted_country:
                            update_data['country'] = extracted_country
                        if extracted_education:
                            update_data['educational_background'] = extracted_education
                        
                        if update_data:
                            Lead.update_lead(lead_id, update_data)
                            self.stats['leads_updated'] += 1
                            self.logger.info(f"Updated lead {lead_id} with: {update_data}")
                    
                    return True, {
                        'lead_id': lead_id,
                        'extracted_info': {
                            'name': extracted_name,
                            'email': extracted_email,
                            'country': extracted_country,
                            'education': extracted_education
                        }
                    }
                            
                except Exception as lead_error:
                    self.logger.error(f"Error managing lead: {lead_error}")
                    
            return False, {'lead_id': lead_id}
            
        except Exception as e:
            self.logger.error(f"Error in lead extraction: {e}")
            return False, {'lead_id': lead_id}
    
    def _is_response_to_dynamic_question(self, conversation_context: Dict) -> bool:
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
    
    def analyze_educational_background(self, text: str) -> Dict[str, Any]:
        """This method is implemented in UserAnalyzer - keeping for interface compatibility"""
        # This is handled by UserAnalyzer now, but keeping for interface compatibility
        return {'education_level': 'unknown', 'field_of_study': 'unknown', 'user_type': 'general'}
    
    def get_stats(self) -> Dict[str, int]:
        """Get lead management statistics"""
        return self.stats.copy()
    
    def health_check(self) -> tuple[bool, str]:
        """Check lead extractor health"""
        try:
            # Test pattern matching
            test_text = "My name is John and I have a bachelor's degree"
            patterns_work = any(keyword in test_text.lower() for keyword in self.personal_info_keywords)
            if patterns_work:
                return True, "Lead extractor is healthy"
            else:
                return False, "Lead extractor pattern matching failed"
        except Exception as e:
            return False, f"Lead extractor health check failed: {e}"
