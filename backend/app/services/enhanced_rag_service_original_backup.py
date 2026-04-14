"""
Enhanced RAG Service with X-ID Based White-Label Multi-Tenancy
Combines advanced conversational memory, FAISS vector search, and university isolation
"""

from openai import OpenAI
import logging
from pymongo import MongoClient
from bson.objectid import ObjectId
from gridfs import GridFS
import numpy as np
from typing import List, Dict, Any, Optional
from app.config import Config
from app.models.chat import ChatSession
from app.models.lead import Lead
from app.models import chat_sessions_collection, leads_collection, chunks_collection, universities_collection
from bson import ObjectId
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import random
import re
import hashlib
import time
import os
import json
import pickle
import uuid
  
# Optional ML dependencies with graceful fallback
try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
    VECTOR_SUPPORT = True
except ImportError:
    VECTOR_SUPPORT = False
    faiss = None
    np = None
    SentenceTransformer = None

class EnhancedRAGService:
    """
    White-Label Enhanced RAG service with X-ID based multi-tenancy
    Features: Conversational memory, FAISS vector search, lead management, dynamic questioning
    """

    def __init__(self):
        """Initialize Enhanced RAG Service with X-ID based multi-tenancy and sequential questioning"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize OpenAI client (single instance, no duplication)
        self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Initialize MongoDB and GridFS (single instance, no duplication)
        try:
            self.mongo_client = MongoClient(Config.MONGODB_URI)
            self.db = self.mongo_client[Config.MONGODB_DB_NAME]
            self.fs = GridFS(self.db)
            self.logger.info("MongoDB and GridFS initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize MongoDB/GridFS: {e}")
            raise
        
        # Initialize ML components with graceful fallback
        self.vector_search_available = False
        self.embedder = None
        
        if VECTOR_SUPPORT:
            try:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
                self.vector_search_available = True
                self.logger.info("Enhanced RAG initialized with vector search capabilities")
            except Exception as e:
                self.vector_search_available = False
                self.embedder = None
                self.logger.warning(f"Vector search initialization failed: {e}")
        else:
            self.logger.info("Enhanced RAG initialized without vector search (dependencies not available)")
        
        # OPTIMIZATION: Use different models for different tasks
        self.main_model = getattr(Config, 'OPENAI_MODEL', 'gpt-4o')  # For main responses
        self.extraction_model = getattr(Config, 'EXTRACTION_MODEL', 'gpt-3.5-turbo')  # Cheaper for extractions
        
        self.temperature = getattr(Config, 'LLM_TEMPERATURE', 0.7)
        # OPTIMIZATION: Reduced max tokens
        self.max_tokens = getattr(Config, 'MAX_TOKENS', 3000)
        self.extraction_max_tokens = 1500

        # OPTIMIZATION: Simple response cache to avoid duplicate API calls
        self.response_cache = {}
        self.cache_ttl = 3600  # 1 hour cache

        # OPTIMIZATION: Personal info extraction keywords for smart filtering
        self.personal_info_keywords = [
            'name', 'email', 'country', 'from', 'called', 'address', 'phone', 'mobile',
            'nationality', 'location', 'my name is', "i'm", "call me", 'completed', 
            'graduated', 'degree', 'bachelor', 'master', 'btech', 'mtech', 'phd',
            'diploma', 'engineering', 'background', 'studied', 'qualification'
        ]

        self.education_patterns = {
            'bachelor_level': [
                'completed bachelor', 'graduated bachelor', 'have bachelor', 'did bachelor',
                'completed btech', 'graduated btech', 'have btech', 'did btech',
                'completed be', 'graduated be', 'have be', 'did be',
                'b.tech', 'btech', 'bachelor of', 'undergraduate'
            ],
            'master_level': [
                'completed master', 'graduated master', 'have master', 'did master',
                'completed mtech', 'graduated mtech', 'have mtech', 'did mtech',
                'm.tech', 'mtech', 'master of', 'mba', 'postgraduate'
            ],
            'engineering_fields': [
                'ece', 'cse', 'mechanical', 'electrical', 'civil', 'chemical', 'it', 'computer',
                'engineering department', 'technology background', 'engineering background'
            ],
            'business_fields': [
                'business', 'commerce', 'management', 'finance', 'marketing', 'economics'
            ]
        }

        self.response_templates = {
            "engineering_graduate": {
                "intro_pattern": "As an engineering graduate, you have excellent opportunities to advance your career.",
                "focus_areas": ["technology management", "business transition", "technical leadership"]
            },
            "business_graduate": {
                "intro_pattern": "With your business background, you can explore advanced specializations.",
                "focus_areas": ["specialized masters", "executive programs", "professional certifications"]
            },
            "working_professional": {
                "intro_pattern": "As a working professional, you can advance your career through our programs.",
                "focus_areas": ["executive education", "leadership programs", "professional certifications"]
            },
            "fresh_graduate": {
                "intro_pattern": "As a recent graduate, you have exciting opportunities for further education.",
                "focus_areas": ["masters programs", "professional certifications", "specialized training"]
            },
            "general": {
                "intro_pattern": "Here are the educational opportunities available:",
                "focus_areas": ["all programs", "comprehensive guidance"]
            }
        }
        

        # Configuration flags for optimization features
        self.enable_smart_filtering = getattr(Config, 'ENABLE_SMART_FILTERING', True)
        self.enable_response_cache = getattr(Config, 'ENABLE_RESPONSE_CACHE', True)
        self.skip_extraction_for_simple_messages = getattr(Config, 'SKIP_EXTRACTION_FOR_SIMPLE_MESSAGES', True)
        self.minimum_message_length = getattr(Config, 'MINIMUM_MESSAGE_LENGTH', 3)

        # Advanced conversation settings
        self.conversation_memory_size = getattr(Config, 'CONVERSATION_MEMORY_SIZE', 8)  # Number of messages to remember
        self.max_conversation_history_chars = getattr(Config, 'MAX_CONVERSATION_HISTORY_CHARS', 300)  # Per message
        self.max_document_context_chars = getattr(Config, 'MAX_DOCUMENT_CONTEXT_CHARS', 1500)  # Document context limit

        # Initialize statistics tracking
        self.stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'api_calls_saved': 0,
            'vector_searches': 0,
            'keyword_searches': 0,
            'leads_created': 0,
            'conversations_started': 0,
            'questions_asked': 0,
            'questions_answered': 0
        }

        # Session-based question state tracking
        self.session_question_state = {}

        # Dynamic questions for white-label personalization
        self.dynamic_questions = {
            "user_name": [
                "By the way, I'd love to personalize our conversation - what should I call you?",
                "To help me assist you better, may I know your name?",
                "I'd like to make this more personal - could you share your name with me?",
                "What name would you like me to use when we're chatting?",
                "I'd be happy to help you more personally - what's your name?"
            ],
            "educational_background": [
                "To suggest the most relevant programs, could you tell me about your educational background?",
                "What's your current or most recent educational qualification?",
                "Could you share your academic background so I can recommend suitable programs?",
                "What degree or qualification do you currently hold?",
                "To provide better guidance, what's your educational background?"
            ],
            "user_email": [
                "If you'd like, I can share some detailed information via email later - what's your email address?",
                "Could you share your email? That way I can send you additional resources if needed.",
                "What's the best email to reach you at if I have more information to share?",
                "If you're comfortable sharing, what's your email address for any follow-up information?"
            ],
            "user_country": [
                "I'd love to provide country-specific information - where are you from?",
                "To give you the most relevant details, which country are you currently in?",
                "Could you tell me your country of origin so I can tailor my advice?",
                "Which country would you be applying from? This helps me provide better guidance."
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

        self.logger.info(f"""Enhanced RAG Service initialized successfully:
        - Vector Search: {'Available' if self.vector_search_available else 'Unavailable'}
        - Smart Filtering: {'Enabled' if self.enable_smart_filtering else 'Disabled'}  
        - Response Caching: {'Enabled' if self.enable_response_cache else 'Disabled'}
        - Sequential Questioning: Enabled (6 phases)
        - Educational Background Analysis: Enabled
        - Response Templates: 4 user types supported
        - Main Model: {self.main_model}
        - Extraction Model: {self.extraction_model}
        """)
        
        # Test greeting detection immediately
        test_questions = ["hello", "hi", "hey"]
        for test_q in test_questions:
            is_greeting = self._is_greeting_or_simple(test_q)
            self.logger.info(f"GREETING TEST: '{test_q}' → {'GREETING' if is_greeting else 'QUERY'}")

    def _analyze_educational_background(self, text: str) -> Dict[str, Any]:
        """Analyze user's educational background from text"""
        try:
            text_lower = text.lower()
            analysis = {
                'education_level': 'unknown',
                'field_of_study': 'unknown',
                'user_type': 'general',
                'specific_degree': '',
                'progression_suggestions': []
            }
            
            # Detect education level
            for level, keywords in self.education_patterns.items():
                if any(keyword in text_lower for keyword in keywords):
                    if level.endswith('_level'):
                        analysis['education_level'] = level.replace('_level', '')
                    elif level.endswith('_fields'):
                        analysis['field_of_study'] = level.replace('_fields', '')
                        # Extract specific degree mentioned
                        for keyword in keywords:
                            if keyword in text_lower:
                                analysis['specific_degree'] = keyword.upper()
                                break
            
            # Determine user type and progression suggestions
            if analysis['education_level'] == 'bachelor':
                if analysis['field_of_study'] == 'engineering':
                    analysis['user_type'] = 'engineering_graduate'
                    analysis['progression_suggestions'] = ['masters_in_engineering', 'mba_tech', 'professional_certifications']
                elif analysis['field_of_study'] == 'business':
                    analysis['user_type'] = 'business_graduate'
                    analysis['progression_suggestions'] = ['specialized_masters', 'professional_certifications']
                else:
                    analysis['user_type'] = 'fresh_graduate'
                    analysis['progression_suggestions'] = ['masters', 'professional_certifications']
            elif analysis['education_level'] == 'master':
                analysis['user_type'] = 'working_professional'
                analysis['progression_suggestions'] = ['executive_programs', 'doctoral_programs', 'professional_certifications']
            
            self.logger.debug(f"Educational background analysis: {analysis}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing educational background: {e}")
            return {'education_level': 'unknown', 'field_of_study': 'unknown', 'user_type': 'general'}

    def _filter_programs_by_background(self, documents: List[Dict[str, Any]], user_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter and score programs based on user's educational background"""
        try:
            if user_analysis['education_level'] == 'unknown':
                return documents
            
            filtered_docs = []
            education_level = user_analysis['education_level']
            field_of_study = user_analysis['field_of_study']
            
            for doc in documents:
                text_lower = doc.get('text', '').lower()
                score = 0
                relevance_reasons = []
                
                # Score based on appropriate education level
                if education_level == 'bachelor':
                    # Look for postgraduate programs
                    if any(term in text_lower for term in ['master', 'mba', 'postgraduate', 'pg']):
                        score += 20
                        relevance_reasons.append('postgraduate_level_appropriate')
                    # Penalize bachelor's programs for bachelor's holders
                    if any(term in text_lower for term in ['bachelor', 'undergraduate', 'ug']) and not any(term in text_lower for term in ['master', 'mba']):
                        score -= 10
                        
                elif education_level == 'master':
                    # Look for executive or advanced programs
                    if any(term in text_lower for term in ['executive', 'advanced', 'professional', 'certificate']):
                        score += 15
                        relevance_reasons.append('advanced_level_appropriate')
                
                # Score based on field relevance
                if field_of_study == 'engineering':
                    if any(term in text_lower for term in ['technology', 'engineering', 'technical', 'digital', 'systems', 'computing']):
                        score += 15
                        relevance_reasons.append('field_relevant')
                    if any(term in text_lower for term in ['business', 'management', 'mba']):
                        score += 10  # Good for career transition
                        relevance_reasons.append('career_transition_suitable')
                        
                elif field_of_study == 'business':
                    if any(term in text_lower for term in ['business', 'management', 'finance', 'marketing', 'commerce']):
                        score += 15
                        relevance_reasons.append('field_relevant')
                
                # Add metadata
                if score > 0:
                    doc['metadata'] = doc.get('metadata', {})
                    doc['metadata']['background_relevance_score'] = score
                    doc['metadata']['relevance_reasons'] = relevance_reasons
                    filtered_docs.append((score, doc))
            
            # Sort by relevance score and return top results
            filtered_docs.sort(key=lambda x: x[0], reverse=True)
            result = [doc for score, doc in filtered_docs[:6]]
            
            self.logger.info(f"Filtered {len(documents)} to {len(result)} programs based on {education_level} in {field_of_study}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error filtering programs by background: {e}")
            return documents

    def _format_response_by_user_type(self, response_content: str, user_analysis: Dict[str, Any], 
                                    user_name: str = "", university_name: str = "") -> str:
        """Format response based on user type and background"""
        try:
            user_type = user_analysis.get('user_type', 'general')
            education_level = user_analysis.get('education_level', 'unknown')
            
            # Only use specific templates if we have actual evidence of user background
            if education_level == 'unknown' or user_type == 'general':
                template = self.response_templates['general']
                user_type = 'general'
            else:
                template = self.response_templates.get(user_type, self.response_templates['general'])
            
            # Create personalized intro only if we have actual user information
            field = user_analysis.get('specific_degree', user_analysis.get('field_of_study', ''))
            if field and field != 'unknown' and user_type != 'general':
                intro = template['intro_pattern'].format(field=field)
            else:
                intro = template['intro_pattern']
            
            # Structure the response better
            lines = response_content.split('\n')
            structured_response = []
            
            # Add personalized intro only if we have a name AND specific user type
            if user_name and user_type != 'general':
                structured_response.append(f"Hi {user_name}! {intro}")
                structured_response.append("")  # Empty line after personalized intro
            elif user_name:
                structured_response.append(f"Hi {user_name}! {intro}")
                structured_response.append("")  # Empty line after generic intro with name
            else:
                # Only add intro if it's not making assumptions
                if user_type != 'general':
                    structured_response.append(intro)
                    structured_response.append("")  # Empty line only if we added intro
                # For general users without name, let the main content speak for itself
            
            # Add context-aware content introduction only if we have evidence
            if user_analysis['education_level'] == 'bachelor':
                structured_response.append("Based on your educational background, here are the most relevant advancement options:")
                structured_response.append("")
            elif user_analysis['education_level'] == 'master':
                structured_response.append("For someone with your qualifications, here are excellent career advancement opportunities:")
                structured_response.append("")
            elif user_analysis['education_level'] != 'unknown':
                structured_response.append("Here are some great educational opportunities for you:")
                structured_response.append("")
            # For unknown education level, don't add any assumption-based introduction
            # and don't add extra spacing
            
            # Process and improve the main content
            current_section = []
            for line in lines:
                line = line.strip()
                if not line:
                    if current_section:
                        structured_response.extend(current_section)
                        structured_response.append("")
                        current_section = []
                else:
                    # Improve formatting of key information
                    if any(keyword in line.lower() for keyword in ['program', 'degree', 'course']):
                        line = f"🎓 **{line}**"
                    elif any(keyword in line.lower() for keyword in ['duration', 'months', 'years']):
                        line = f"⏱️ {line}"
                    elif any(keyword in line.lower() for keyword in ['fee', 'cost', 'price']):
                        line = f"💰 {line}"
                    elif any(keyword in line.lower() for keyword in ['requirement', 'eligibility']):
                        line = f"📋 {line}"
                    
                    current_section.append(line)
            
            # Add remaining content
            if current_section:
                structured_response.extend(current_section)
            
            # Add call-to-action based on user type (only if we have evidence)
            structured_response.append("")
            if user_analysis['education_level'] == 'bachelor':
                structured_response.append("💡 **Next Steps:** Which of these advancement paths interests you most? I can provide detailed information about admission requirements, career prospects, and application processes!")
            elif user_analysis['education_level'] != 'unknown':
                structured_response.append("💡 **Ready to Take the Next Step?** I'm here to help with detailed information about any program that catches your interest!")
            else:
                # Generic call-to-action when we don't know the user's background
                structured_response.append("💡 **How Can I Help?** I can provide detailed information about any program that interests you - just let me know what you'd like to learn more about!")
            
            return "\n".join(structured_response)
            
        except Exception as e:
            self.logger.error(f"Error formatting response by user type: {e}")
            return response_content

    def query(self, question: str, university_code: str = None, session_id: str = None, 
              lead_id: str = None, is_first_message: bool = False, university_x_id: str = None) -> Dict[str, Any]:
        """
        Enhanced query method with X-ID based white-label support
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Enhanced RAG query - X-ID: {university_x_id}, Code: {university_code}, Session: {session_id}")
            
            # Resolve university information
            if not university_x_id and university_code:
                from app.models.university import University
                university = University.get_university_by_code(university_code)
                if university and university.get('x_id'):
                    university_x_id = university['x_id']
                    self.logger.debug(f"Resolved X-ID {university_x_id} from university code {university_code}")
            
            if not university_x_id and not university_code:
                return {
                    "answer": "I apologize, but I need university information to assist you properly.",
                    "error": "No university identifier provided",
                    "processing_time": time.time() - start_time
                }

            # Get conversation context for enhanced responses
            conversation_context = self._get_conversation_context(session_id, lead_id) if session_id else {}
            
            # Handle greeting or simple responses
            self.logger.info(f"CHECKING if '{question}' is a greeting...")
            if self._is_greeting_or_simple(question):
                self.logger.info(f"GREETING CONFIRMED - generating greeting response for: '{question}'")
                greeting_response = self._generate_greeting_response(question, university_x_id, conversation_context)
                greeting_response.update({
                    "university_x_id": university_x_id,
                    "session_id": session_id,
                    "lead_id": lead_id,
                    "processing_time": time.time() - start_time,
                    "from_cache": False,
                    "search_method": "greeting_handler"
                })
                self.logger.info(f"RETURNING greeting response: {greeting_response.get('answer', '')[:100]}...")
                return greeting_response
            else:
                self.logger.info(f"NOT A GREETING - proceeding with full RAG for: '{question}'")

            # Check cache first
            context_summary = f"x_id:{university_x_id}_len:{conversation_context.get('conversation_length', 0)}"
            cache_key = self._get_cache_key(question, university_x_id or university_code, context_summary)
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                self.logger.info("Returning cached response - API calls saved!")
                cached_response.update({
                    "university_x_id": university_x_id,
                    "session_id": session_id,
                    "lead_id": lead_id,
                    "from_cache": True,
                    "processing_time": time.time() - start_time
                })
                return cached_response

            # Smart filtering for cost optimization
            self.logger.info(f"DEBUG: About to check if should skip extraction for: '{question}'")
            skip_extraction = self._should_skip_expensive_extraction(question, conversation_context)
            self.logger.info(f"DEBUG: Skip extraction decision: {skip_extraction}")
            
            extracted_lead_id = None
            if not skip_extraction:
                self.logger.info(f"DEBUG: Starting lead extraction for question: '{question}'")
                extracted_lead_id = self._extract_and_manage_lead_optimized(
                    question, session_id, lead_id, university_code, conversation_context
                )
                self.logger.info(f"DEBUG: Lead extraction result: {extracted_lead_id}")
            else:
                self.logger.info(f"DEBUG: Skipped lead extraction for: '{question}'")
            
            # Update lead_id if a new lead was created
            if extracted_lead_id and not lead_id:
                lead_id = extracted_lead_id
                conversation_context = self._get_conversation_context(session_id, lead_id)
                self.logger.info(f"DEBUG: Updated session with new lead_id: {lead_id}")
            else:
                self.logger.info(f"DEBUG: No lead_id update needed - extracted: {extracted_lead_id}, existing: {lead_id}")

            # NEW: Check if this was a simple response to a dynamic question
            # If so, generate acknowledgment response instead of full RAG
            if self._is_simple_dynamic_response(question, conversation_context, extracted_lead_id is not None):
                self.logger.info(f"Detected simple dynamic response, generating acknowledgment instead of full RAG for: '{question}'")
                acknowledgment_response = self._generate_dynamic_response_acknowledgment(
                    question, conversation_context, university_x_id, session_id
                )
                
                # Update conversation memory for acknowledgment response
                self._update_conversation_memory(session_id, lead_id, question, acknowledgment_response)
                
                # Add dynamic question if appropriate for acknowledgment responses
                dynamic_question = self._get_dynamic_question(conversation_context, question, False, session_id)
                if dynamic_question:
                    acknowledgment_response['answer'] += f"\n\n---\n\n💬 **{dynamic_question}**"
                    acknowledgment_response['contains_question'] = True
                    acknowledgment_response['dynamic_question_text'] = dynamic_question
                    self.logger.info(f"Added dynamic question to acknowledgment response")
                
                acknowledgment_response.update({
                    "university_x_id": university_x_id,
                    "session_id": session_id,
                    "lead_id": lead_id,
                    "processing_time": time.time() - start_time,
                    "from_cache": False,
                    "search_method": "dynamic_response_acknowledgment"
                })
                return acknowledgment_response

            # Load university documents
            documents = self._get_university_documents(university_code, university_x_id)
            
            if not documents:
                fallback_response = self._get_fallback_response(university_x_id)
                return {
                    "answer": fallback_response,
                    "source_documents": [],
                    "university_x_id": university_x_id,
                    "session_id": session_id,
                    "lead_id": lead_id,
                    "processing_time": time.time() - start_time,
                    "warning": "No documents available"
                }

            # NEW: Analyze educational background from conversation context and current question
            user_analysis = {'education_level': 'unknown', 'field_of_study': 'unknown', 'user_type': 'general'}
            try:
                # Combine current question with conversation history for analysis
                analysis_text = question
                if conversation_context.get('message_history'):
                    recent_messages = conversation_context['message_history'][-3:]  # Last 3 messages
                    for msg in recent_messages:
                        if msg.get('role') == 'user':
                            analysis_text += " " + msg.get('content', '')
                
                user_analysis = self._analyze_educational_background(analysis_text)
                self.logger.info(f"User analysis: {user_analysis['user_type']} with {user_analysis['education_level']} in {user_analysis['field_of_study']}")
            except Exception as e:
                self.logger.warning(f"Educational background analysis failed: {e}")

            # Enhanced document search - now gets up to 8 documents
            relevant_docs = self._enhanced_document_search(question, documents, university_x_id)
            
            # NEW: Filter documents based on user background
            if user_analysis['education_level'] != 'unknown':
                try:
                    filtered_docs = self._filter_programs_by_background(relevant_docs, user_analysis)
                    if filtered_docs:
                        relevant_docs = filtered_docs
                        self.logger.info(f"Applied background filtering: {len(filtered_docs)} relevant programs for {user_analysis['user_type']}")
                except Exception as e:
                    self.logger.warning(f"Program filtering failed, using all documents: {e}")
            
            # Create COMPREHENSIVE document context - using more documents
            doc_context = "\n\n" + "="*50 + "\n\n".join([
                f"DOCUMENT {i+1} - SOURCE: {doc.get('source', 'Unknown')}\nRELEVANCE SCORE: {doc.get('metadata', {}).get('similarity_score', 'N/A')}\nCONTENT:\n{doc.get('text', '')}" 
                for i, doc in enumerate(relevant_docs[:6])  # Use up to 6 documents for comprehensive context
            ]) + "\n\n" + "="*50
            
            self.logger.info(f"Created comprehensive context from {len(relevant_docs)} documents ({len(doc_context)} chars)")
            
            # Generate conversational response (using the optimized method with user analysis)
            response = self._generate_conversational_response_optimized(
                question, doc_context, conversation_context, university_code, is_first_message, university_x_id, user_analysis
            )
            
            # Update conversation memory
            self._update_conversation_memory(session_id, lead_id, question, response)
            
            # Add dynamic question if appropriate - KEEP SEPARATE FROM MAIN CONTENT
            dynamic_question = self._get_dynamic_question(conversation_context, question, is_first_message, session_id)
            if dynamic_question:
                # Separate dynamic questions with clear spacing for better UX
                response['answer'] += f"\n\n---\n\n💬 **{dynamic_question}**"
                response['contains_question'] = True
                response['dynamic_question_text'] = dynamic_question
                self.logger.info(f"Added dynamic question to response (separated)")
            else:
                self.logger.debug(f"No dynamic question added - Context: {conversation_context.get('conversation_length', 0)} turns, Session: {session_id}")
            
            # Complete response
            response.update({
                "source_documents": self._format_documents(relevant_docs),
                "university_code": university_code,
                "university_x_id": university_x_id,
                "session_id": session_id,
                "lead_id": lead_id,
                "processing_time": time.time() - start_time,
                "from_cache": False,
                "documents_processed": len(documents),
                "relevant_documents": len(relevant_docs),
                "search_method": relevant_docs[0]['metadata'].get('search_method') if relevant_docs else 'none'
            })
            
            # Cache the response
            if self.enable_response_cache:
                self._cache_response(cache_key, response)
            
            self.logger.info(f"Query completed successfully in {time.time() - start_time:.2f}s")
            return response

        except Exception as e:
            self.logger.error(f"Error in query processing: {e}", exc_info=True)
            return {
                "answer": self._get_fallback_response(university_x_id if 'university_x_id' in locals() else None),
                "error": str(e),
                "processing_time": time.time() - start_time if 'start_time' in locals() else 0
            }

    def _is_greeting_or_simple(self, question: str) -> bool:
        """Check if the question is a greeting or simple response - FIXED VERSION"""
        if not question or len(question.strip()) < 2:
            return True
            
        question_lower = question.lower().strip()
        
        # FIXED: Use word boundaries and exact patterns instead of substring matching
        import re
        
        # Strict greeting patterns with word boundaries
        greeting_patterns = [
            r'^(hi|hello|hey)[\s\.,!]*$',            # Standalone greetings only
            r'^(good\s+(morning|afternoon|evening|day))[\s\.,!]*$',  # Time-based greetings 
            r'^(thanks?|thank\s+you)[\s\.,!]*$',     # Thank you messages
            r'^(ok|okay|yes|no)[\s\.,!]*$',          # Simple confirmations
            r'^(bye|goodbye|see\s+you)[\s\.,!]*$'    # Farewell messages
        ]
        
        # Check against patterns
        for pattern in greeting_patterns:
            if re.match(pattern, question_lower):
                self.logger.info(f"GREETING detected: '{question}' (matched pattern: {pattern})")
                return True
        
        # Additional check for very short messages
        if len(question_lower) <= 3:
            self.logger.info(f"GREETING detected: '{question}' (short message)")
            return True
        
        self.logger.info(f"REAL QUERY detected: '{question}'")
        return False
        

    def _enhanced_document_search(self, question: str, documents: List[Dict[str, Any]], university_x_id: str = None) -> List[Dict[str, Any]]:
        """Enhanced document search with better keyword matching and scoring"""
        try:
            # Try vector search first if available
            if university_x_id and self.vector_search_available:
                vector_results = self._find_relevant_documents_vector(question, university_x_id, top_k=8)
                if vector_results:
                    self.logger.info(f"Vector search found {len(vector_results)} relevant documents")
                    return vector_results
            
            # Enhanced keyword matching with better scoring
            self.logger.info(f"Performing enhanced keyword search for: '{question}'")
            question_lower = question.lower()
            scored_docs = []
            
            # Extract key terms from question - improved extraction
            stop_words = {'what', 'how', 'when', 'where', 'why', 'who', 'the', 'is', 'are', 'can', 'do', 'does', 'have', 'has', 'you', 'your', 'about', 'for', 'in', 'on', 'at', 'to'}
            question_words = [word for word in question_lower.split() if len(word) > 2 and word not in stop_words]
            
            self.logger.debug(f"Key search terms: {question_words}")
            
            for doc in documents:
                text_lower = doc.get('text', '').lower()
                score = 0
                matched_terms = []

                # Multi-level scoring system - IMPROVED
                for word in question_words:
                    word_count = text_lower.count(word)
                    if word_count > 0:
                        # Higher score for more important terms
                        if word in ['course', 'program', 'degree', 'fee', 'cost', 'admission', 'requirement']:
                            score += word_count * 5  # High importance terms
                        else:
                            score += word_count * 3  # Base score for word matches
                        matched_terms.append(word)

                # Bonus for exact phrase matches - IMPROVED
                if len(question) > 10:
                    # Try to find partial phrase matches
                    phrase_parts = question_lower.split()
                    for i in range(len(phrase_parts) - 1):
                        two_word_phrase = f"{phrase_parts[i]} {phrase_parts[i+1]}"
                        if two_word_phrase in text_lower:
                            score += 15  # Bonus for 2-word phrase match
                    
                    # Full phrase bonus
                    if question_lower in text_lower:
                        score += 25

                # Bonus for multiple term matches - IMPROVED
                if len(matched_terms) > 1:
                    score += len(matched_terms) * 3
                
                # Bonus for document relevance based on source type
                source = doc.get('source', '').lower()
                if any(keyword in source for keyword in ['course', 'program', 'curriculum', 'academic']):
                    score += 5

                # Add to scored documents if relevant
                if score > 0:
                    doc['metadata'] = doc.get('metadata', {})
                    doc['metadata']['similarity_score'] = score
                    doc['metadata']['matched_terms'] = matched_terms
                    doc['metadata']['match_density'] = len(matched_terms) / len(question_words) if question_words else 0
                    scored_docs.append((score, doc))

            # Sort by score and return top results - INCREASED to 8 for better coverage
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            relevant_docs = [doc for score, doc in scored_docs[:8]]
            
            if relevant_docs:
                self.logger.info(f"Enhanced search found {len(relevant_docs)} relevant documents with scores: {[doc['metadata']['similarity_score'] for doc in relevant_docs[:5]]}")
            else:
                self.logger.warning(f"No relevant documents found, using fallback")
                relevant_docs = documents[:4]  # Fallback to first 4 documents
            
            return relevant_docs

        except Exception as e:
            self.logger.error(f"Error in enhanced document search: {e}")
            return documents[:4]  # Safe fallback

    def _generate_detailed_response(self, question: str, doc_context: str, conversation_context: Dict, 
                                  university_x_id: str = None, relevant_docs: List = None) -> Dict[str, Any]:
        """Generate detailed, document-based response for real queries"""
        try:
            # Get university information
            university_info = {}
            if university_x_id:
                university = universities_collection.find_one({"x_id": university_x_id})
                if university:
                    university_info = {
                        "name": university.get('name', 'our university'),
                        "code": university.get('code', 'UNI')
                    }
            
            university_name = university_info.get('name', 'our university')
            user_name = conversation_context.get('user_info', {}).get('name', '')
            
            # Enhanced prompt for detailed responses
            system_prompt = f"""You are an AI assistant for {university_name} designed to help prospective students with admissions information. 
            You have access to comprehensive university documents and provide helpful, detailed guidance.

            IMPORTANT INSTRUCTIONS:
            1. Use ONLY the information provided in the university documents
            2. Be specific and detailed in your responses
            3. If the user asks about programs, list specific program names and details
            4. If they ask about fees, provide exact amounts when available
            5. If they ask about requirements, list all relevant criteria
            6. Always be helpful and encouraging
            7. If specific information isn't in the documents, acknowledge this and offer to help with related topics
            8. Keep responses conversational and engaging
            9. Use the student's name ({user_name}) if available to personalize the response
            10. IMPORTANT: You are an AI assistant - do not add signatures, salutations, or formal closings like "Warm regards" or "Best wishes"
            11. End responses naturally without formal sign-offs
            """

            user_prompt = f"""Based on the university documents provided, please answer this student's question comprehensively:

            UNIVERSITY DOCUMENTS:
            {doc_context}

            STUDENT QUESTION: {question}

            Please provide a detailed, helpful response based on the university documents. If specific information like program names, fees, or requirements are mentioned in the documents, include them in your response.
            """
            
            response = self.openai_client.chat.completions.create(
                model=self.main_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for more factual responses
                max_tokens=600    # Adequate for detailed responses
            )
            
            answer = response.choices[0].message.content
            
            # Add source information if we have good matches
            source_info = ""
            if relevant_docs:
                high_quality_docs = [doc for doc in relevant_docs if doc.get('metadata', {}).get('similarity_score', 0) > 10]
                if high_quality_docs:
                    sources = list(set([doc.get('source', 'university document') for doc in high_quality_docs[:2]]))
                    source_info = f"\n\n*Information sourced from: {', '.join(sources)}*"
            
            final_answer = answer + source_info
            
            self.logger.info(f"Generated detailed response ({len(final_answer)} chars) for query: '{question[:50]}...'")
            
            return {
                "answer": final_answer,
                "response_type": "detailed_document_based",
                "sources_used": len(relevant_docs) if relevant_docs else 0,
                "context_length": len(doc_context),
                "university_branded": True
            }
            
        except Exception as e:
            self.logger.error(f"Error generating detailed response: {e}")
            # Fallback response
            return {
                "answer": f"Thank you for your question about {university_name}. I'd be happy to help you with detailed information about our programs and services. Could you please rephrase your question so I can provide you with the most accurate information?",
                "response_type": "fallback_error",
                "error": str(e)
            }

    def _generate_greeting_response(self, question: str, university_x_id: str, context: Dict) -> Dict[str, Any]:
        """Generate appropriate greeting response with university branding"""
        try:
            self.logger.info(f"GENERATING greeting response for: '{question}'")
            
            # Get university information for personalized greeting
            university = universities_collection.find_one({"x_id": university_x_id}) if university_x_id else None
            university_name = university.get('name', 'our university') if university else 'our university'
            
            user_name = context.get('user_info', {}).get('name', '')
            greeting_part = f"Hi{' ' + user_name if user_name else ''}! "
            
            question_lower = question.lower().strip()
            
            if any(greeting in question_lower for greeting in ['hi', 'hello', 'hey']):
                response = f"{greeting_part}Welcome to {university_name}! 🎓 I'm here to help you with information about our programs, admissions, and any questions you might have. How can I assist you today?"
            elif any(thanks in question_lower for thanks in ['thanks', 'thank you']):
                response = f"You're very welcome{' ' + user_name if user_name else ''}! I'm happy to help with any questions about {university_name}. Is there anything else you'd like to know?"
            elif any(bye in question_lower for bye in ['bye', 'goodbye']):
                response = f"Goodbye{' ' + user_name if user_name else ''}! Thank you for your interest in {university_name}. Feel free to return anytime if you have more questions. 👋"
            else:
                response = f"{greeting_part}I'm your AI assistant for {university_name}. How can I help you today?"
            
            self.logger.info(f"GREETING RESPONSE generated: '{response[:100]}...'")
            
            return {
                "answer": response,
                "response_type": "greeting",
                "conversation_context": context
            }
        except Exception as e:
            self.logger.error(f"ERROR generating greeting response: {e}")
            return {
                "answer": "Hello! How can I help you today?",
                "response_type": "greeting_fallback"
            }

    def _should_skip_expensive_extraction(self, question: str, conversation_context: Dict) -> bool:
        """
        FIXED: Conservative extraction filtering - defaults to NOT skipping
        Only skips extraction for obvious non-personal messages
        """
        try:
            # Always extract if smart filtering is disabled
            if not self.enable_smart_filtering:
                return False
        
            # STEP 1: Basic validation - only skip if message is invalid
            if not question or len(question.strip()) < 1:
                self.logger.debug("Skipping extraction - empty/invalid message")
                return True
        
            question_clean = question.strip()
            question_lower = question_clean.lower()
        
            # STEP 2: NEVER skip if personal information keywords are present
            personal_keywords_found = any(keyword in question_lower for keyword in self.personal_info_keywords)
            if personal_keywords_found:
                self.logger.debug(f"NOT skipping - found personal keywords in: '{question_clean}'")
                return False
        
            # STEP 3: NEVER skip if contains name introduction patterns
            name_intro_patterns = [
                r'\bmy name is\b', r'\bi\'m [a-zA-Z]', r'\bcall me\b', r'\bi am [a-zA-Z]',
                r'\bname is\b', r'\bhello.*i\'m\b', r'\bhi.*i\'m\b'
            ]
            for pattern in name_intro_patterns:
                if re.search(pattern, question_lower):
                    self.logger.debug(f"NOT skipping - found name pattern: {pattern}")
                    return False
        
            # STEP 4: NEVER skip if contains email patterns
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
            if re.search(email_pattern, question):
                self.logger.debug("NOT skipping - found email pattern")
                return False
        
            # STEP 5: NEVER skip if this is a response to a dynamic question
            if self._is_response_to_dynamic_question(conversation_context):
                self.logger.debug("NOT skipping - response to dynamic question")
                return False
        
            # STEP 6: NEVER skip if message contains potential personal names (capitalized words)
            # But be more specific - look for reasonable name patterns
            if len(question_clean.split()) <= 3:  # Short messages that could be names
                words = question_clean.split()
                for word in words:
                    # Check if word looks like a name (capitalized, reasonable length)
                    if (word[0].isupper() and len(word) > 1 and len(word) <= 20 and 
                        word.isalpha() and word.lower() not in ['hi', 'hello', 'hey', 'yes', 'no', 'ok', 'thanks']):
                        self.logger.debug(f"NOT skipping - potential name detected: '{word}'")
                        return False
        
            # STEP 7: NEVER skip if message is longer (could contain personal info)
            if len(question_clean.split()) > 5:  # More than 5 words - likely contains info
                self.logger.debug(f"NOT skipping - longer message: {len(question_clean.split())} words")
                return False
        
            # STEP 8: ONLY skip for these specific obvious non-personal cases
            obvious_skip_cases = [
                'hi', 'hello', 'hey', 'yes', 'no', 'ok', 'okay', 'thanks', 'thank you',
                'bye', 'goodbye', 'sure', 'alright', 'got it', 'i see', 'hmm', 'ohh'
            ]
        
            if question_lower in obvious_skip_cases:
                self.logger.debug(f"Skipping extraction - obvious non-personal: '{question_lower}'")
                return True
        
            # STEP 9: Conservative default - when in doubt, extract!
            self.logger.debug(f"NOT skipping (conservative default) - extracting from: '{question_clean}'")
            return False
        
        except Exception as e:
            self.logger.error(f"Error in smart filtering: {e}")
            # On error, be conservative - don't skip extraction
            return False

    def _is_response_to_dynamic_question(self, conversation_context: Dict) -> bool:
        """Check if the current message appears to be a response to a recent dynamic question"""
        try:
            message_history = conversation_context.get('message_history', [])
            if not message_history:
                return False
            
            # Check the last assistant message for dynamic question indicators
            for msg in reversed(message_history[-3:]):  # Check last 3 messages
                if msg.get('role') == 'assistant':
                    content = msg.get('content', '').lower()
                    # Check if it contains dynamic question patterns
                    question_indicators = [
                        'what should i call you',
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

    def _is_simple_dynamic_response(self, question: str, conversation_context: Dict, lead_extracted: bool) -> bool:
        """Check if this is a simple response to a recent dynamic question"""
        try:
            # If no lead was extracted, it's probably not a simple info response
            if not lead_extracted:
                return False
            
            # Check if this appears to be a response to a dynamic question
            if not self._is_response_to_dynamic_question(conversation_context):
                return False
            
            # Check if the response is relatively simple (not a complex query)
            question_words = len(question.strip().split())
            if question_words > 15:  # If more than 15 words, probably not a simple response
                return False
            
            # Check if it contains university-related query keywords that suggest they want info
            university_keywords = [
                'program', 'course', 'degree', 'admission', 'fee', 'requirement', 
                'duration', 'curriculum', 'apply', 'application', 'scholarship',
                'tuition', 'campus', 'facility', 'placement', 'job', 'career'
            ]
            
            question_lower = question.lower()
            if any(keyword in question_lower for keyword in university_keywords):
                return False  # They're asking about university info, not just responding
            
            self.logger.debug(f"Detected simple dynamic response: '{question}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking for simple dynamic response: {e}")
            return False

    def _generate_dynamic_response_acknowledgment(self, question: str, conversation_context: Dict, 
                                                university_x_id: str, session_id: str) -> Dict[str, Any]:
        """Generate a brief acknowledgment for simple dynamic question responses"""
        try:
            # Get university info for personalization
            from app.models.university import University
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
            import random
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

    def _extract_and_manage_lead_optimized(self, question: str, session_id: str, lead_id: str, 
                                           university_code: str, conversation_context: Dict) -> Optional[str]:
        """Extract personal details and manage leads efficiently"""
        try:
            # If we already have a lead_id, check if we need to update it
            if lead_id:
                question_lower = question.lower()
                has_personal_keywords = any(keyword in question_lower for keyword in self.personal_info_keywords)
                if not has_personal_keywords:
                    return lead_id

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
                r"i am (\w+)"
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
                            country=extracted_country or "Unknown"
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
                            update_data['education_background'] = extracted_education
                        
                        if update_data:
                            Lead.update_lead(lead_id, update_data)
                            self.logger.info(f"Updated lead {lead_id} with: {update_data}")
                            
                    return lead_id
                    
                except Exception as lead_error:
                    self.logger.error(f"Error managing lead: {lead_error}")
                    
            return lead_id
            
        except Exception as e:
            self.logger.error(f"Error in lead extraction: {e}")
            return lead_id

    def _get_dynamic_question(self, conversation_context: Dict, question: str, 
                            is_first_message: bool, session_id: str) -> Optional[str]:
        """Get dynamic question based on conversation state with sequential ordering"""
        try:
            if not self.questioning_config.get("enable_dynamic_questioning", True):
                return None
            
            # Get user info from context
            user_info = conversation_context.get('user_info', {})
            conversation_length = conversation_context.get('conversation_length', 0)
            
            # Initialize session state if needed
            if session_id not in self.session_question_state:
                self.session_question_state[session_id] = {
                    "questions_asked": [],
                    "last_question_turn": 0,
                    "failed_attempts": {},
                    "phase": 1
                }
            
            session_state = self.session_question_state[session_id]
            
            # Get next question category based on sequential order
            next_question_category = self._get_next_question_category(user_info, session_state, conversation_length)
            
            if next_question_category:
                questions_list = self.dynamic_questions.get(next_question_category, [])
                
                if questions_list:
                    selected_question = random.choice(questions_list)
                    
                    # Update session state
                    if session_id:
                        session_state["questions_asked"].append(next_question_category)
                        session_state["last_question_turn"] = conversation_length
                        self.session_question_state[session_id] = session_state
                    
                    # Update stats
                    if hasattr(self, 'stats'):
                        self.stats["questions_asked"] = self.stats.get("questions_asked", 0) + 1
                    
                    self.logger.debug(f"Sequential question asked: {next_question_category} at turn {conversation_length}")
                    return selected_question
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting dynamic question: {e}")
            return None

    def _generate_conversational_response_optimized(self, question: str, doc_context: str, 
                                                   conversation_context: Dict, university_code: str, 
                                                   is_first_message: bool = False, university_x_id: str = None, 
                                                   user_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate conversational response with optimization and university branding"""
        try:
            # Get university information for branding
            university_info = {}
            if university_x_id:
                university = universities_collection.find_one({"x_id": university_x_id})
                if university:
                    university_info = {
                        "name": university.get('name', 'our university'),
                        "code": university.get('code', 'UNI'),
                        "x_id": university_x_id
                    }
            
            university_name = university_info.get('name', 'our university')
            user_info = conversation_context.get('user_info', {})
            user_name = user_info.get('name', '')
            
            # Use user analysis if available, default to conservative values
            if not user_analysis:
                user_analysis = {'education_level': 'unknown', 'field_of_study': 'unknown', 'user_type': 'general'}
            
            # Be conservative - only apply specific guidance if we have clear evidence
            if user_analysis.get('education_level') == 'unknown':
                user_analysis['user_type'] = 'general'
            
            # Build conversation history for context
            conv_history = ""
            if conversation_context.get('message_history'):
                recent_messages = conversation_context['message_history'][-4:]  # Last 4 messages
                conv_history = "\n".join([
                    f"{msg.get('role', 'user').upper()}: {msg.get('content', '')[:200]}" 
                    for msg in recent_messages
                ])
            
            # Create system prompt - conservative when we lack user information
            if user_analysis.get('education_level') != 'unknown' and user_analysis.get('user_type') != 'general':
                # Detailed prompt when we have user information
                system_prompt = f"""You are an AI assistant for {university_name} designed to help prospective students with admissions information. 
                You have access to comprehensive university documents and provide helpful, detailed guidance.

                STUDENT PROFILE:
                - Name: {user_name if user_name else 'Not provided yet'}
                - Education Level: {user_analysis.get('education_level', 'Unknown')}
                - Field of Study: {user_analysis.get('field_of_study', 'Unknown')}
                - User Type: {user_analysis.get('user_type', 'General')}
                - Country: {user_info.get('country', 'Not specified')}

                RESPONSE GUIDELINES:
                1. PRIORITIZE programs appropriate for the student's educational level:
                   - For Bachelor's degree holders: Focus on Master's, MBA, and postgraduate programs
                   - For Master's degree holders: Focus on executive programs, professional certifications
                2. For engineering graduates: Emphasize technology-business bridge programs, advanced engineering, MBA
                3. For business graduates: Focus on specializations and advanced business programs
                4. Use clear, structured formatting for better readability
                5. Always explain the progression logic and career benefits
                6. IMPORTANT: You are an AI assistant - do not add signatures, salutations, or formal closings like "Warm regards" or "Best wishes"
                7. End responses naturally without formal sign-offs
                """
            else:
                # Conservative prompt when we don't have user information
                system_prompt = f"""You are an AI assistant for {university_name} designed to help prospective students with admissions information. 
                You have access to comprehensive university documents and provide helpful, detailed guidance.

                RESPONSE GUIDELINES:
                1. Provide comprehensive information about all available programs
                2. Use clear, structured formatting for better readability
                3. Be warm and helpful without making assumptions about the student's background
                4. Include program details like duration, requirements, and structure
                5. Be encouraging and professional
                6. Don't assume the student's education level or career goals unless explicitly stated
                7. IMPORTANT: You are an AI assistant - do not add signatures, salutations, or formal closings like "Warm regards" or "Best wishes"
                8. End responses naturally without formal sign-offs
                """

            # Add conversation context if available
            if conv_history:
                system_prompt += f"\n\nCONVERSATION CONTEXT:\nRecent conversation: {conv_history}"

            # Conservative user prompt when we don't have background info
            if user_analysis.get('education_level') != 'unknown' and user_analysis.get('user_type') != 'general':
                user_prompt = f"""Based on the comprehensive university documents provided, please give a detailed and helpful response to this question considering the student's background.
                
                UNIVERSITY DOCUMENTS:
                {doc_context}

                STUDENT'S QUESTION: {question}

                Please provide a comprehensive response that:
                1. Prioritizes programs appropriate for their educational level
                2. Includes specific details like program names, fees, requirements when available
                3. Explains why these programs suit their background
                4. Is well-structured and easy to read
                5. Shows enthusiasm for {university_name}"""
            else:
                user_prompt = f"""Based on the comprehensive university documents provided, please give a detailed and helpful response to this question.
                
                UNIVERSITY DOCUMENTS:
                {doc_context}

                STUDENT'S QUESTION: {question}

                Please provide a comprehensive response that:
                1. Answers the question thoroughly using document information
                2. Includes specific details like program names, fees, requirements when available
                3. Presents all relevant programs without assumptions about student level
                4. Is well-structured and easy to read
                5. Shows enthusiasm for {university_name}
                6. Avoids making assumptions about the student's background or goals"""
            
            # Generate response using OpenAI with higher max tokens for comprehensive responses
            response = self.openai_client.chat.completions.create(
                model=self.main_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4,  # Slightly lower for more factual, detailed responses
                max_tokens=800    # Increased for more comprehensive responses
            )
            
            answer = response.choices[0].message.content.strip()
            
            # NEW: Apply user-type based formatting for better UX
            try:
                formatted_answer = self._format_response_by_user_type(answer, user_analysis, user_name, university_name)
                final_answer = formatted_answer
                self.logger.info(f"Applied {user_analysis.get('user_type', 'general')} formatting to response")
            except Exception as format_error:
                self.logger.warning(f"Response formatting failed, using original: {format_error}")
                # Add source attribution for transparency
                source_note = "\n\n*Information provided is based on official university documents and materials.*"
                final_answer = answer + source_note
            
            self.logger.info(f"Generated comprehensive response ({len(final_answer)} chars)")
            
            return {
                "answer": final_answer,
                "conversation_aware": True,
                "university_branded": True,
                "user_personalized": bool(user_name),
                "response_type": "comprehensive_conversational",
                "university_name": university_name,
                "response_length": len(final_answer),
                "topics": conversation_context.get('topics_discussed', []),
                "user_analysis": user_analysis,
                "background_filtered": user_analysis.get('education_level') != 'unknown',
                "user_type_formatted": True
            }
            
        except Exception as e:
            self.logger.error(f"Error generating conversational response: {e}", exc_info=True)
            fallback_name = university_info.get('name', 'our university') if 'university_info' in locals() else 'our university'
            return {
                "answer": f"Thank you for your question about {fallback_name}. I'd be happy to help you with detailed information about our programs, admissions, and facilities. Could you please let me know what specific aspect interests you most?",
                "conversation_aware": False,
                "response_type": "fallback_error",
                "error": str(e)
            }

    def _find_relevant_documents(self, question: str, documents: List[Dict[str, Any]], 
                               university_x_id: str = None) -> List[Dict[str, Any]]:
        """Find relevant documents using hybrid approach (vector + keyword)"""
        try:
            # Try enhanced document search first
            relevant_docs = self._enhanced_document_search(question, documents, university_x_id)
            
            if relevant_docs:
                return relevant_docs
            
            # Fallback to simple keyword matching
            question_lower = question.lower()
            scored_docs = []
            
            for doc in documents:
                text_lower = doc.get('text', '').lower()
                score = 0
                
                # Simple keyword scoring
                question_words = [word for word in question_lower.split() if len(word) > 2]
                for word in question_words:
                    if word in text_lower:
                        score += text_lower.count(word) * 2
                
                if score > 0:
                    doc['relevance_score'] = score
                    scored_docs.append((score, doc))
            
            # Sort by relevance and return top results
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            relevant_docs = [doc for score, doc in scored_docs[:4]]
            
            self.logger.debug(f"Simple keyword search returned {len(relevant_docs)} relevant documents")
            return relevant_docs

        except Exception as e:
            self.logger.error(f"Error finding relevant documents: {e}")
            return documents[:4]

    def _find_next_sequential_question(self, user_info: Dict, session_state: Dict, conversation_length: int) -> Optional[Dict]:
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

    def _update_question_state_on_response(self, session_id: str, question_asked: str, user_response: str):
        """Update questioning state when user responds to a question"""
        try:
            if not session_id or session_id not in self.session_question_state:
                return
            
            session_state = self.session_question_state[session_id]
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
            
            self.session_question_state[session_id] = session_state
            
        except Exception as e:
            self.logger.error(f"Error updating question state: {e}")

    def _get_dynamic_question_sequential(self, conversation_context: Dict, current_question: str, 
                                       is_first_message: bool = False, session_id: str = None) -> Optional[str]:
        """Get the next appropriate question based on sequential order and conversation state"""
        try:
            conversation_length = conversation_context.get("conversation_length", 0)
            user_info = conversation_context.get("user_info", {})
            
            # Initialize session state if not exists
            if session_id and session_id not in self.session_question_state:
                self.session_question_state[session_id] = {
                    "questions_asked": [],
                    "questions_answered": [],
                    "failed_attempts": {},
                    "last_question_turn": 0,
                    "phase": 1
                }
            
            session_state = self.session_question_state.get(session_id, {})
            
            # Don't ask questions too frequently - maintain natural conversation flow
            turns_since_last_question = conversation_length - session_state.get("last_question_turn", 0)
            if turns_since_last_question < self.questioning_config["ask_questions_every_n_turns"] and not is_first_message:
                return None
            
            # Check if we've asked enough questions
            total_questions_asked = len(session_state.get("questions_asked", []))
            if total_questions_asked >= self.questioning_config["max_questions_per_conversation"]:
                return None
            
            # Find the next question to ask based on sequence
            next_question = self._find_next_sequential_question(user_info, session_state, conversation_length)
            
            if next_question:
                question_category = next_question["category"]
                questions_list = self.dynamic_questions.get(question_category, [])
                
                if questions_list:
                    selected_question = random.choice(questions_list)
                    
                    # Update session state
                    if session_id:
                        session_state["questions_asked"].append(question_category)
                        session_state["last_question_turn"] = conversation_length
                        session_state["phase"] = next_question["priority"]
                        self.session_question_state[session_id] = session_state
                    
                    self.stats["questions_asked"] += 1
                    self.logger.debug(f"Sequential question asked: {question_category} (Phase {next_question['priority']})")
                    return selected_question
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in sequential dynamic questioning: {e}")
            return None
        """Determine the next question category to ask based on sequential order"""
        questions_asked = set(session_state.get("questions_asked", []))
        failed_attempts = session_state.get("failed_attempts", {})
        
        # Phase 1: REQUIRED personal information - CORRECT ORDER
        
        # 1. FIRST: Always ask for name if not available
        if "user_name" not in questions_asked and not user_info.get('name'):
            if conversation_length >= 1:  # Ask from turn 1
                return "user_name"
        
        # 2. SECOND: Ask for email after name
        if ("user_email" not in questions_asked and 
            user_info.get('name') and  # Have name
            conversation_length >= 3):  # Ask from turn 3
            
            # Check if we have a real email (not placeholder)
            email = user_info.get('email', '')
            if not email or email.startswith('temp_') or '@placeholder.com' in email:
                return "user_email"
        
        # 3. THIRD: Ask for country after email
        if ("user_country" not in questions_asked and 
            user_info.get('name') and  # Have name
            user_info.get('email') and  # Have email
            conversation_length >= 5):  # Ask from turn 5
            
            # Check if we have real country info
            country = user_info.get('country', '')
            if not country or country == 'Unknown':
                return "user_country"
        
        # Phase 2: OPTIONAL academic and preference information
        
        # 4. Academic interests
        if ("academic_interests" not in questions_asked and 
            user_info.get('name') and user_info.get('email') and user_info.get('country') and
            conversation_length >= 7):
            return "academic_interests"
        
    def _get_next_question_category(self, user_info: Dict, session_state: Dict, conversation_length: int) -> Optional[str]:
        """Determine the next question category to ask based on sequential order"""
        questions_asked = set(session_state.get("questions_asked", []))
        failed_attempts = session_state.get("failed_attempts", {})
        
        self.logger.debug(f"🔍 Question category check - Asked: {questions_asked}, User: {user_info}")
        
        # Phase 1: REQUIRED personal information - CORRECT ORDER
        
        # 1. FIRST: Always ask for name if not available (MOST IMPORTANT)
        if "user_name" not in questions_asked and not user_info.get('name'):
            if conversation_length >= 1:  # Ask from turn 1
                self.logger.debug("✅ Next question: user_name")
                return "user_name"
        
        # 2. SECOND: Ask for educational background after name
        if ("educational_background" not in questions_asked and 
            user_info.get('name') and  # Have name
            conversation_length >= 2):  # Ask from turn 2
            self.logger.debug("✅ Next question: educational_background")
            return "educational_background"
        
        # 3. THIRD: Ask for email after educational background
        if ("user_email" not in questions_asked and 
            user_info.get('name') and  # Have name
            conversation_length >= 4):  # Ask from turn 4
            
            # Check if we have a real email (not placeholder)
            email = user_info.get('email', '')
            if not email or email.startswith('temp_') or '@placeholder.com' in email:
                self.logger.debug("✅ Next question: user_email")
                return "user_email"
        
        # 4. FOURTH: Ask for country after email
        if ("user_country" not in questions_asked and 
            user_info.get('name') and  # Have name
            user_info.get('email') and  # Have email
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
        
        self.logger.debug("❌ No next question category found")
        return None

    def _get_university_documents(self, university_code: str = None, university_x_id: str = None) -> List[Dict[str, Any]]:
        """Get documents for a university using X-ID based approach with legacy fallback"""
        try:
            # Resolve university X-ID if only code provided
            if not university_x_id and university_code:
                from app.models.university import University
                university = University.get_university_by_code(university_code)
                if university and university.get('x_id'):
                    university_x_id = university['x_id']
                else:
                    self.logger.warning(f"Could not resolve X-ID for university code: {university_code}")
                    return self._get_legacy_documents(university_code)
            
            if not university_x_id:
                self.logger.warning("No university X-ID provided for document retrieval")
                return []
            
            documents = []
            
            # Primary: Get chunks from enhanced PDF service
            try:
                chunks = list(chunks_collection.find({"university_x_id": university_x_id}))
                
                if chunks:
                    self.logger.debug(f"Using enhanced chunks for X-ID {university_x_id}: {len(chunks)} chunks")
                    for chunk in chunks:
                        documents.append({
                            'text': chunk.get('text', ''),
                            'source': chunk.get('metadata', {}).get('source_file', 'Unknown'),
                            'chunk_id': chunk.get('chunk_id'),
                            'metadata': {
                                'search_method': 'enhanced_chunks',
                                'university_x_id': university_x_id,
                                'source_file': chunk.get('metadata', {}).get('source_file', 'Unknown')
                            }
                        })
                    return documents
                else:
                    self.logger.debug(f"No enhanced chunks found for X-ID {university_x_id}")
            except Exception as e:
                self.logger.error(f"Error accessing enhanced chunks for {university_x_id}: {e}")
            
            # Fallback: Use legacy documents collection
            try:
                from app.models.university import University
                legacy_docs = University.get_university_documents_by_x_id(university_x_id)
                
                if legacy_docs:
                    self.logger.debug(f"Using legacy documents for X-ID {university_x_id}: {len(legacy_docs)} documents")
                    for doc in legacy_docs:
                        documents.append({
                            'text': doc.get('content', ''),
                            'source': doc.get('title', 'Unknown Document'),
                            'metadata': {
                                'search_method': 'legacy_documents',
                                'university_x_id': university_x_id,
                                'document_type': doc.get('type', 'unknown')
                            }
                        })
                else:
                    self.logger.warning(f"No documents found for X-ID {university_x_id}")
            except Exception as e:
                self.logger.error(f"Error accessing legacy documents for {university_x_id}: {e}")
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Error in _get_university_documents: {e}")
            return []

    def _get_legacy_documents(self, university_code: str) -> List[Dict[str, Any]]:
        """Fallback method for legacy document retrieval by university code"""
        try:
            from app.models.university import University
            documents = University.get_university_documents(university_code)
            
            formatted_docs = []
            for doc in documents:
                formatted_docs.append({
                    'text': doc.get('content', ''),
                    'source': doc.get('title', 'Unknown Document'),
                    'metadata': {
                        'search_method': 'legacy_by_code',
                        'university_code': university_code,
                        'document_type': doc.get('type', 'unknown')
                    }
                })
            
            self.logger.debug(f"Retrieved {len(formatted_docs)} legacy documents for code {university_code}")
            return formatted_docs
            
        except Exception as e:
            self.logger.error(f"Error in _get_legacy_documents: {e}")
            return []

    def _find_relevant_documents_vector(self, question: str, university_x_id: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Find relevant documents using FAISS vector search for the specific university_x_id."""
        try:
            if not self.vector_search_available:
                return []
                
            self.logger.debug(f"Vector search for university X-ID: {university_x_id}, question: {question[:100]}...")
            
            # Load FAISS index for this university
            index = self._load_faiss_index(university_x_id)
            if not index:
                self.logger.debug(f"No FAISS index available for {university_x_id}")
                return []

            # Fetch chunks strictly for this university_x_id
            chunks = list(chunks_collection.find({"university_x_id": university_x_id}))
            if not chunks:
                self.logger.debug(f"No chunks found for university X-ID: {university_x_id}")
                return []

            self.logger.debug(f"Found {len(chunks)} chunks for university X-ID: {university_x_id}")
            
            # Verify index-chunk alignment
            if index.ntotal != len(chunks):
                self.logger.error(f"Index mismatch for {university_x_id}: FAISS has {index.ntotal} vectors, but {len(chunks)} chunks found")
                return []

            # Generate query embedding
            query_embedding = self.embedder.encode([question])[0].astype('float32')
            query_embedding = np.expand_dims(query_embedding, axis=0)
            
            # Search FAISS index
            scores, indices = index.search(query_embedding, min(top_k, len(chunks)))
            
            # Build results
            relevant_docs = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if 0 <= idx < len(chunks):
                    chunk = chunks[idx]
                    relevant_docs.append({
                        'text': chunk.get('text', ''),
                        'source': chunk.get('metadata', {}).get('source_file', 'Unknown'),
                        'similarity_score': float(score),
                        'rank': i + 1,
                        'chunk_id': chunk.get('chunk_id'),
                        'metadata': {
                            'search_method': 'vector_faiss',
                            'university_x_id': university_x_id,
                            'similarity_score': float(score)
                        }
                    })
            
            self.logger.debug(f"Vector search returned {len(relevant_docs)} relevant documents for {university_x_id}")
            return relevant_docs
            
        except Exception as e:
            self.logger.error(f"Error in vector search for {university_x_id}: {str(e)}", exc_info=True)
            return []

    def _load_faiss_index(self, university_x_id: str):
        """Load FAISS index from GridFS for the given university_x_id with enhanced error handling."""
        if not self.vector_search_available:
            self.logger.debug(f"Vector search not available for {university_x_id}")
            return None
            
        try:
            self.logger.debug(f"Loading FAISS index for university X-ID: {university_x_id}")
            
            # Get university and check for FAISS index
            university = universities_collection.find_one({"x_id": university_x_id})
            if not university:
                self.logger.warning(f"University with X-ID '{university_x_id}' not found")
                return None
                
            if "gridfs_faiss_index" not in university:
                self.logger.debug(f"No FAISS index found for university X-ID: {university_x_id}")
                return None

            faiss_file_id = university["gridfs_faiss_index"]
            self.logger.debug(f"Retrieving FAISS index from GridFS file: {faiss_file_id}")
            
            grid_file = self.fs.get(ObjectId(faiss_file_id))
            index_bytes = grid_file.read()
            self.logger.debug(f"Read {len(index_bytes)} bytes from GridFS for FAISS index")

            # Deserialize FAISS index
            index = faiss.deserialize_index(np.frombuffer(index_bytes, dtype=np.uint8))
            self.logger.debug(f"Successfully loaded FAISS index with {index.ntotal} vectors for {university_x_id}")
            return index
            
        except Exception as e:
            self.logger.error(f"Error loading FAISS index for {university_x_id}: {str(e)}", exc_info=True)
            return None

    def _get_fallback_response(self, university_x_id: str = None) -> str:
        """Generate fallback response when AI processing fails"""
        from app.models.university import University
        university = University.get_university_by_x_id(university_x_id) if university_x_id else None
        university_name = university.get('name', 'our university') if university else 'our university'
        
        return f"I'm here to help you learn about {university_name}! I can assist with questions about our academic programs, admissions process, campus facilities, fees and scholarships, student life, and much more. What specific information would you like to know?"

    def _get_conversation_context(self, session_id: str, lead_id: str = None) -> dict:
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

    def _update_conversation_memory(self, session_id: str, lead_id: str, question: str, response: dict):
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
                
                # NEW: Update question state tracking
                if response.get("contains_question"):
                    assistant_message = response.get("answer", "")
                    self._update_question_state_on_response(session_id, assistant_message, question)
                
        except Exception as e:
            self.logger.error(f"Error updating conversation memory: {e}")

    def _get_cache_key(self, question: str, university_id: str, context_summary: str) -> str:
        """Generate cache key for response caching"""
        try:
            key_data = f"{question}_{university_id}_{context_summary}"
            return hashlib.md5(key_data.encode()).hexdigest()
        except Exception as e:
            self.logger.error(f"Error generating cache key: {e}")
            return f"fallback_{int(time.time())}"

    def _get_cached_response(self, cache_key: str) -> Optional[dict]:
        """Get cached response if available"""
        try:
            if not self.enable_response_cache:
                return None
                
            if cache_key in self.response_cache:
                cached_item = self.response_cache[cache_key]
                if time.time() - cached_item['timestamp'] < self.cache_ttl:
                    self.stats['cache_hits'] += 1
                    return cached_item['response']
                else:
                    del self.response_cache[cache_key]
        except Exception as e:
            self.logger.error(f"Error retrieving cached response: {e}")
        return None

    def _cache_response(self, cache_key: str, response: Dict[str, Any]):
        """Cache response for future use with enhanced cleanup"""
        try:
            self.response_cache[cache_key] = {
                'response': response,
                'timestamp': time.time()
            }
            
            # Enhanced cache cleanup - more efficient
            if len(self.response_cache) > 100:
                # Remove oldest entries more efficiently
                sorted_cache = sorted(
                    self.response_cache.items(), 
                    key=lambda x: x[1]['timestamp']
                )
                # Keep only the 50 most recent entries
                self.response_cache = dict(sorted_cache[-50:])
                self.logger.debug("Cache cleanup performed - kept 50 most recent entries")
                
        except Exception as e:
            self.logger.error(f"Error caching response: {e}")

    def _format_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format documents for response"""
        formatted = []
        for i, doc in enumerate(documents):
            formatted.append({
                'chunk_text': doc.get('text', '')[:1000],
                'metadata': doc.get('metadata', {}),
                'chunk_index': i,
                'source': doc.get('source', 'unknown'),
                'similarity_score': doc.get('similarity_score', 0)
            })
        return formatted

    def get_rag_stats(self, university_code: str = None, university_x_id: str = None) -> Dict[str, Any]:
        """Get RAG service statistics for analytics"""
        try:
            # Basic service stats
            service_stats = {
                "service_info": {
                    "vector_search_available": self.vector_search_available,
                    "main_model": self.main_model,
                    "extraction_model": self.extraction_model,
                    "cache_enabled": self.enable_response_cache,
                    "smart_filtering_enabled": self.enable_smart_filtering
                },
                "usage_stats": self.stats.copy(),
                "performance_metrics": {
                    "cache_hit_rate": (self.stats['cache_hits'] / max(self.stats['total_queries'], 1)) * 100,
                    "active_sessions": len(self.session_question_state),
                    "cache_size": len(self.response_cache)
                }
            }
            
            # University-specific stats if X-ID provided
            if university_x_id:
                university_stats = self._get_university_specific_stats(university_x_id)
                service_stats["university_stats"] = university_stats
            
            return service_stats
            
        except Exception as e:
            self.logger.error(f"Error getting RAG stats: {e}")
            return {"error": str(e)}

    def _get_university_specific_stats(self, university_x_id: str) -> Dict[str, Any]:
        """Get statistics specific to a university"""
        try:
            stats = {
                "document_stats": {
                    "total_chunks": 0,
                    "has_vector_index": False,
                    "last_updated": None
                },
                "capabilities": {
                    "vector_search": False,
                    "document_retrieval": False,
                    "conversational_memory": True
                }
            }
            
            # Check chunks
            try:
                chunk_count = chunks_collection.count_documents({"university_x_id": university_x_id})
                stats["document_stats"]["total_chunks"] = chunk_count
                stats["capabilities"]["document_retrieval"] = chunk_count > 0
            except Exception as e:
                self.logger.warning(f"Error getting chunk stats for {university_x_id}: {e}")
            
            # Check FAISS index
            try:
                university = universities_collection.find_one({"x_id": university_x_id})
                if university and "gridfs_faiss_index" in university:
                    stats["document_stats"]["has_vector_index"] = True
                    stats["capabilities"]["vector_search"] = self.vector_search_available
            except Exception as e:
                self.logger.warning(f"Error checking FAISS index for {university_x_id}: {e}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting university stats: {e}")
            return {"error": str(e)}

    def health_check(self) -> tuple[bool, str]:
        """Check if the enhanced RAG service is healthy"""
        try:
            if not self.openai_client.api_key:
                return False, "OpenAI API key not configured"
            
            # Check vector search availability
            vector_status = "available" if self.vector_search_available else "unavailable"
            
            # Check database connectivity
            try:
                universities_collection.find_one()
                db_status = "connected"
            except Exception:
                db_status = "disconnected"
                return False, f"Database connection failed"
            
            # Check basic functionality
            try:
                test_response = self._generate_greeting_response("hi", None, {})
                if not test_response.get('answer'):
                    return False, "Basic response generation failed"
            except Exception as test_error:
                return False, f"Response generation test failed: {str(test_error)}"
            
            return True, f"Enhanced RAG Service healthy - Vector search: {vector_status}, Database: {db_status}, Cache: {len(self.response_cache)} items"
            
        except Exception as e:
            return False, f"Health check failed: {str(e)}"

    def clear_cache(self):
        """Clear response cache"""
        try:
            cache_size = len(self.response_cache)
            self.response_cache.clear()
            self.logger.info(f"Cleared {cache_size} cached responses")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
            return False

    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get current state for a session"""
        try:
            if session_id in self.session_question_state:
                return self.session_question_state[session_id].copy()
            return {}
        except Exception as e:
            self.logger.error(f"Error getting session state: {e}")
            return {}

    def reset_session_state(self, session_id: str):
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

    def clear_conversation_memory(self, session_id: str) -> bool:
        """Clear conversation memory for a session"""
        try:
            # Clear session-specific question state
            if session_id in self.session_question_state:
                del self.session_question_state[session_id]
            
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
            context = self._get_conversation_context(session_id)
            
            return {
                "total_messages": len(messages),
                "topics_discussed": context.get("topics_discussed", []),
                "user_info_collected": context.get("user_info", {}),
                "session_duration": "estimated_duration",
                "last_updated": session.get("updated_at"),
                "university_x_id": session.get("university_x_id"),
                "enhanced_features_used": {
                    "vector_search": self.vector_search_available,
                    "conversation_memory": True,
                    "lead_management": bool(context.get("user_info", {}).get("name")),
                    "dynamic_questioning": self.questioning_config.get("enable_dynamic_questioning", True)
                },
                "questioning_state": self.session_question_state.get(session_id, {})
            }
            
        except Exception as e:
            self.logger.error(f"Error getting conversation summary: {e}")
            return {"error": str(e)}

    def update_stats(self, stat_name: str, increment: int = 1):
        """Update service statistics"""
        try:
            if stat_name in self.stats:
                self.stats[stat_name] += increment
            else:
                self.stats[stat_name] = increment
        except Exception as e:
            self.logger.error(f"Error updating stats: {e}")

    def get_service_metrics(self) -> Dict[str, Any]:
        """Get comprehensive service metrics"""
        try:
            return {
                "service_info": {
                    "name": "Enhanced RAG Service",
                    "version": "2.0",
                    "capabilities": {
                        "vector_search": self.vector_search_available,
                        "conversational_memory": True,
                        "lead_management": True,
                        "dynamic_questioning": True,
                        "cost_optimization": self.enable_smart_filtering,
                        "response_caching": self.enable_response_cache
                    }
                },
                "performance_metrics": {
                    "total_queries": self.stats.get('total_queries', 0),
                    "cache_hits": self.stats.get('cache_hits', 0),
                    "cache_hit_rate": (self.stats.get('cache_hits', 0) / max(self.stats.get('total_queries', 1), 1)) * 100,
                    "active_sessions": len(self.session_question_state),
                    "cache_size": len(self.response_cache),
                    "leads_created": self.stats.get('leads_created', 0),
                    "questions_asked": self.stats.get('questions_asked', 0),
                    "api_calls_saved": self.stats.get('api_calls_saved', 0)
                },
                "configuration": {
                    "main_model": self.main_model,
                    "extraction_model": self.extraction_model,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "questioning_enabled": self.questioning_config.get("enable_dynamic_questioning", True),
                    "max_questions_per_conversation": self.questioning_config.get("max_questions_per_conversation", 7)
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting service metrics: {e}")
            return {"error": str(e)}

    def optimize_performance(self):
        """Perform performance optimizations"""
        try:
            optimizations_performed = []
            
            # Clear old cache entries
            if len(self.response_cache) > 50:
                # Keep only the 25 most recent entries
                sorted_cache = sorted(
                    self.response_cache.items(), 
                    key=lambda x: x[1]['timestamp'], 
                    reverse=True
                )
                self.response_cache = dict(sorted_cache[:25])
                optimizations_performed.append("cache_cleanup")
            
            # Clear old session states (older than 24 hours)
            current_time = time.time()
            old_sessions = []
            for session_id, state in self.session_question_state.items():
                # If session hasn't been active for more than 24 hours, remove it
                if current_time - state.get("last_question_turn", 0) > 86400:  # 24 hours
                    old_sessions.append(session_id)
            
            for session_id in old_sessions:
                del self.session_question_state[session_id]
            
            if old_sessions:
                optimizations_performed.append(f"removed_{len(old_sessions)}_old_sessions")
            
            self.logger.info(f"Performance optimization completed: {optimizations_performed}")
            return {
                "success": True,
                "optimizations": optimizations_performed,
                "cache_size": len(self.response_cache),
                "active_sessions": len(self.session_question_state)
            }
            
        except Exception as e:
            self.logger.error(f"Error during performance optimization: {e}")
            return {"success": False, "error": str(e)}