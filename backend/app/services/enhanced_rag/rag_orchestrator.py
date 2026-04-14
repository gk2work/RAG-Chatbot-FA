"""
Main RAG service orchestrator that coordinates all Enhanced RAG components
"""

import logging
import time
import re
from typing import Dict, List, Any, Optional, Tuple
from openai import OpenAI
from pymongo import MongoClient
from gridfs import GridFS

from app.config import Config
from app.models.chat import ChatSession
from app.models.lead import Lead
from app.models import chat_sessions_collection, leads_collection, chunks_collection, universities_collection

# Import all the modular components
from .vector_search import FAISSManager, EmbeddingService
from .lead_management import LeadExtractor, UserAnalyzer
from .conversation import MemoryManager, SessionStateManager
from .document_search import DocumentFinder, ContentFilter
from .response_generation import ResponseFormatter, LLMClient
from .questioning import DynamicQuestioner, SequenceManager
from .utils import CacheManager, PerformanceMonitor


class EnhancedRAGService:
    """
    Enhanced RAG service orchestrator that coordinates all modular components
    Features: Conversational memory, FAISS vector search, lead management, dynamic questioning
    """

    def __init__(self):
        """Initialize Enhanced RAG Service with modular components"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize MongoDB and GridFS
        try:
            self.mongo_client = MongoClient(Config.MONGODB_URI)
            self.db = self.mongo_client[Config.MONGODB_DB_NAME]
            self.fs = GridFS(self.db)
            self.logger.info("MongoDB and GridFS initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize MongoDB/GridFS: {e}")
            raise
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Configuration
        self.main_model = getattr(Config, 'OPENAI_MODEL', 'gpt-4o')
        self.extraction_model = getattr(Config, 'EXTRACTION_MODEL', 'gpt-3.5-turbo')
        self.temperature = getattr(Config, 'LLM_TEMPERATURE', 0.7)
        self.max_tokens = getattr(Config, 'MAX_TOKENS', 3000)
        self.conversation_memory_size = 10
        
        # Feature flags
        self.enable_smart_filtering = getattr(Config, 'ENABLE_SMART_FILTERING', True)
        self.enable_response_cache = getattr(Config, 'ENABLE_RESPONSE_CACHE', True)
        
        # Initialize all modular components
        self._initialize_components()
        
        # Personal info extraction keywords for smart filtering
        self.personal_info_keywords = [
            'name', 'email', 'country', 'from', 'called', 'address', 'phone', 'mobile',
            'nationality', 'location', 'my name is', "i'm", "call me", 'completed', 
            'graduated', 'degree', 'bachelor', 'master', 'btech', 'mtech', 'phd',
            'diploma', 'engineering', 'background', 'studied', 'qualification'
        ]
        
        self.logger.info(f"""Enhanced RAG Service initialized successfully with modular architecture:
        - Vector Search: {'Available' if self.vector_search_available else 'Unavailable'}
        - Smart Filtering: {'Enabled' if self.enable_smart_filtering else 'Disabled'}  
        - Response Caching: {'Enabled' if self.enable_response_cache else 'Disabled'}
        - Sequential Questioning: Enabled (6 phases)
        - Educational Background Analysis: Enabled
        - Response Templates: 4 user types supported
        - Main Model: {self.main_model}
        - Extraction Model: {self.extraction_model}
        """)
    
    def _initialize_components(self):
        """Initialize all modular components"""
        try:
            # Vector search components
            self.embedding_service = EmbeddingService()
            self.faiss_manager = FAISSManager(self.embedding_service, self.fs)
            self.vector_search_available = self.embedding_service.is_available()
            
            # Lead management components
            self.lead_extractor = LeadExtractor(self.openai_client)
            self.user_analyzer = UserAnalyzer()
            
            # Conversation management components
            self.memory_manager = MemoryManager(self.conversation_memory_size)
            self.session_state_manager = SessionStateManager()
            
            # Document search components
            self.document_finder = DocumentFinder()
            self.content_filter = ContentFilter()
            
            # Response generation components
            self.response_formatter = ResponseFormatter()
            self.llm_client = LLMClient()
            
            # Questioning components
            self.sequence_manager = SequenceManager()
            self.dynamic_questioner = DynamicQuestioner(self.sequence_manager)
            
            # Utility components
            self.cache_manager = CacheManager(self.enable_response_cache)
            self.performance_monitor = PerformanceMonitor()
            
            self.logger.info("All modular components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            raise
    
    def query(self, question: str, university_code: str = None, session_id: str = None, 
              lead_id: str = None, is_first_message: bool = False, university_x_id: str = None) -> Dict[str, Any]:
        """
        Enhanced query method with X-ID based white-label support
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Enhanced RAG query - X-ID: {university_x_id}, Code: {university_code}, Session: {session_id}")
            
            # Update performance stats
            self.performance_monitor.update_stats('total_queries')
            
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
            conversation_context = self.memory_manager.get_conversation_context(session_id, lead_id) if session_id else {}
            
            # Add university information to context for lead extraction
            conversation_context['university_code'] = university_code
            conversation_context['university_x_id'] = university_x_id
            
            # Initialize and add session state to context
            if session_id:
                self.session_state_manager.initialize_session_state(session_id)
                session_state = self.session_state_manager.get_session_state(session_id)
                conversation_context['session_state'] = session_state
                conversation_context['session_id'] = session_id
            else:
                conversation_context['session_state'] = {
                    "questions_asked": [],
                    "last_question_turn": 0,
                    "failed_attempts": {},
                    "phase": 1
                }
                conversation_context['session_id'] = None
            
            # Get user info from lead if available for dynamic questioning
            user_info = {}
            if lead_id:
                from app.models.lead import Lead
                lead_data = Lead.get_lead_by_id(lead_id)
                if lead_data:
                    user_info = {
                        'name': lead_data.get('name') if lead_data.get('name') != 'Unknown' else None,
                        'email': lead_data.get('email') if lead_data.get('email') and not lead_data.get('email').endswith('@placeholder.com') else None,
                        'country': lead_data.get('country') if lead_data.get('country') != 'Unknown' else None,
                        'educational_background': lead_data.get('educational_background')
                    }
            conversation_context['user_info'] = user_info
            
            # Handle greeting or simple responses
            self.logger.info(f"CHECKING if '{question}' is a greeting...")
            if self._is_greeting_or_simple(question):
                self.logger.info(f"GREETING CONFIRMED - generating greeting response for: '{question}'")
                greeting_response = self.response_formatter.generate_greeting_response(question, university_x_id, conversation_context)
                greeting_response.update({
                    "university_x_id": university_x_id,
                    "session_id": session_id,
                    "lead_id": lead_id,
                    "processing_time": time.time() - start_time,
                    "from_cache": False,
                    "search_method": "greeting_handler"
                })
                
                # Update stats
                self.performance_monitor.update_stats('greeting_responses')
                
                # Avoid unicode issues in logging
                answer_preview = greeting_response.get('answer', '')[:100].encode('ascii', 'ignore').decode('ascii')
                self.logger.info(f"RETURNING greeting response: {answer_preview}...")
                return greeting_response
            else:
                self.logger.info(f"NOT A GREETING - proceeding with full RAG for: '{question}'")

            # Check cache first
            context_summary = f"x_id:{university_x_id}_len:{conversation_context.get('conversation_length', 0)}"
            cache_key = self.cache_manager.get_cache_key(question, university_x_id or university_code, context_summary)
            cached_response = self.cache_manager.get_cached_response(cache_key)
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
            
            extracted_lead = None
            if not skip_extraction:
                self.logger.info(f"DEBUG: Starting lead extraction for question: '{question}'")
                lead_extracted, lead_info = self.lead_extractor.extract_and_manage_lead(
                    question, session_id, lead_id, conversation_context
                )
                extracted_lead = lead_info.get('lead_id')
                self.logger.info(f"DEBUG: Lead extraction result: {extracted_lead}")
            else:
                self.logger.info(f"DEBUG: Skipped lead extraction for: '{question}'")
            
            # Update lead_id if a new lead was created
            if extracted_lead and not lead_id:
                lead_id = extracted_lead
                conversation_context = self.memory_manager.get_conversation_context(session_id, lead_id)
                # Re-add university information to context
                conversation_context['university_code'] = university_code
                conversation_context['university_x_id'] = university_x_id
                self.logger.info(f"DEBUG: Updated session with new lead_id: {lead_id}")
            else:
                self.logger.info(f"DEBUG: No lead_id update needed - extracted: {extracted_lead}, existing: {lead_id}")
            
            # CRITICAL: Update user_info in conversation_context after lead extraction
            # This ensures dynamic questioning sees the latest extracted information
            if lead_id:
                from app.models.lead import Lead
                lead_data = Lead.get_lead_by_id(lead_id)
                if lead_data:
                    updated_user_info = {
                        'name': lead_data.get('name') if lead_data.get('name') != 'Unknown' else None,
                        'email': lead_data.get('email') if lead_data.get('email') and not lead_data.get('email').endswith('@placeholder.com') else None,
                        'country': lead_data.get('country') if lead_data.get('country') != 'Unknown' else None,
                        'educational_background': lead_data.get('educational_background')
                    }
                    conversation_context['user_info'] = updated_user_info
                    self.logger.debug(f"🔄 Updated user_info after extraction: {updated_user_info}")

            # NEW: Check if this was a simple response to a dynamic question
            # If so, generate acknowledgment response instead of full RAG
            lead_extracted_flag = lead_extracted if not skip_extraction else False
            if self._is_simple_dynamic_response(question, conversation_context, lead_extracted_flag):
                self.logger.info(f"Detected simple dynamic response, generating acknowledgment instead of full RAG for: '{question}'")
                acknowledgment_response = self.dynamic_questioner.generate_dynamic_response_acknowledgment(
                    question, conversation_context, university_x_id
                )
                
                # Update conversation memory for acknowledgment response
                self.memory_manager.update_conversation_memory(session_id, lead_id, question, acknowledgment_response)
                
                # Add dynamic question if appropriate for acknowledgment responses
                dynamic_question = self.dynamic_questioner.get_dynamic_question(conversation_context, question, university_x_id)
                if dynamic_question:
                    acknowledgment_response['answer'] += f"\n\n---\n\n💬 **{dynamic_question}**"
                    acknowledgment_response['contains_question'] = True
                    acknowledgment_response['dynamic_question_text'] = dynamic_question
                    
                    # Update session state with the question asked
                    if session_id:
                        session_state = self.session_state_manager.get_session_state(session_id)
                        session_state['last_question_turn'] = conversation_context.get('conversation_length', 0)
                        self.session_state_manager.update_session_state(session_id, session_state)
                    
                    self.logger.info(f"Added dynamic question to acknowledgment response")
                
                # Update stats
                self.performance_monitor.update_stats('dynamic_acknowledgments')
                
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
            documents = self.document_finder.get_university_documents(university_code, university_x_id)
            
            if not documents:
                fallback_response = self.response_formatter.format_fallback_response(university_x_id)
                return {
                    "answer": fallback_response,
                    "source_documents": [],
                    "university_x_id": university_x_id,
                    "session_id": session_id,
                    "lead_id": lead_id,
                    "processing_time": time.time() - start_time,
                    "warning": "No documents available"
                }

            # Analyze educational background from conversation context and current question
            user_analysis = {'education_level': 'unknown', 'field_of_study': 'unknown', 'user_type': 'general'}
            try:
                # Only analyze actual user messages, not system prompts or assistant messages
                analysis_text = ""
                
                # Add current question if it's a real user question (not system prompt)
                if not question.startswith("Generate a brief") and not "welcome message" in question.lower():
                    analysis_text = question
                
                # Add previous user messages from conversation history
                if conversation_context.get('message_history'):
                    recent_messages = conversation_context['message_history'][-3:]  # Last 3 messages
                    for msg in recent_messages:
                        if msg.get('role') == 'user':
                            analysis_text += " " + msg.get('content', '')
                
                # Only analyze if we have actual user content
                if not analysis_text.strip():
                    self.logger.debug("No user content to analyze - using default general analysis")
                    user_analysis = {'education_level': 'unknown', 'field_of_study': 'unknown', 'user_type': 'general'}
                else:
                    self.logger.debug(f"Analyzing text for educational background: '{analysis_text[:100]}...'")
                    user_analysis = self.user_analyzer.analyze_educational_background(analysis_text)
                
                # Only log as working_professional if we actually detected something
                if user_analysis['education_level'] != 'unknown' or user_analysis['field_of_study'] != 'unknown':
                    self.logger.info(f"User analysis (detected): {user_analysis['user_type']} with {user_analysis['education_level']} in {user_analysis['field_of_study']}")
                else:
                    self.logger.debug(f"User analysis (no patterns found): {user_analysis['user_type']} - staying general")
            except Exception as e:
                self.logger.warning(f"Educational background analysis failed: {e}")

            # Enhanced document search - try vector search first, then keyword search
            relevant_docs = []
            if self.vector_search_available:
                try:
                    relevant_docs = self.faiss_manager.find_relevant_documents_vector(question, university_x_id, top_k=8)
                    if relevant_docs:
                        self.performance_monitor.update_stats('vector_searches')
                        self.logger.info(f"Vector search found {len(relevant_docs)} relevant documents")
                except Exception as e:
                    self.logger.error(f"Vector search failed: {e}")
            
            # Fallback to keyword search if vector search didn't return results
            if not relevant_docs:
                relevant_docs = self.document_finder.enhanced_document_search(question, documents, university_x_id)
                self.performance_monitor.update_stats('keyword_searches')
                self.logger.info(f"Keyword search found {len(relevant_docs)} relevant documents")

            # Filter documents based on user background
            if user_analysis['education_level'] != 'unknown':
                try:
                    filtered_docs = self.user_analyzer.filter_programs_by_background(relevant_docs, user_analysis)
                    if filtered_docs and len(filtered_docs) >= 3:  # Only use filtered if we have good coverage
                        relevant_docs = filtered_docs
                        self.logger.info(f"Applied educational background filtering: {len(filtered_docs)} programs selected")
                except Exception as e:
                    self.logger.warning(f"Background filtering failed: {e}")
            
            # Apply content filtering
            relevant_docs = self.content_filter.prioritize_high_quality_sources(relevant_docs)
            relevant_docs = self.content_filter.deduplicate_documents(relevant_docs)

            # Prepare document context for LLM
            doc_context = self.content_filter.format_documents_for_context(relevant_docs[:6])  # Limit to top 6 for context
            
            # Generate response using LLM
            response_dict = self._generate_response_with_context(
                question, doc_context, conversation_context, university_x_id, user_analysis, relevant_docs
            )
            
            # Add dynamic question if appropriate
            dynamic_question = self.dynamic_questioner.get_dynamic_question(conversation_context, question, university_x_id)
            if dynamic_question:
                response_dict['answer'] += f"\n\n---\n\n💬 **{dynamic_question}**"
                response_dict['contains_question'] = True
                response_dict['dynamic_question_text'] = dynamic_question
                self.performance_monitor.update_stats('questions_asked')
                
                # Update session state with the question asked
                if session_id:
                    session_state = self.session_state_manager.get_session_state(session_id)
                    session_state['last_question_turn'] = conversation_context.get('conversation_length', 0)
                    self.session_state_manager.update_session_state(session_id, session_state)
                
                self.logger.info(f"Added dynamic question: {dynamic_question}")

            # Update conversation memory
            self.memory_manager.update_conversation_memory(session_id, lead_id, question, response_dict)
            
            # Cache the response
            self.cache_manager.cache_response(cache_key, response_dict)
            
            # Add metadata
            response_dict.update({
                "university_x_id": university_x_id,
                "session_id": session_id,
                "lead_id": lead_id,
                "processing_time": time.time() - start_time,
                "from_cache": False,
                "total_documents": len(documents),
                "relevant_documents": len(relevant_docs),
                "search_method": "vector" if self.vector_search_available and relevant_docs else "keyword",
                "user_analysis": user_analysis,
                "source_documents": self._format_documents_for_response(relevant_docs[:3])  # Top 3 for response
            })
            
            # Update stats
            self.performance_monitor.update_stats('questions_answered')
            if response_dict.get('response_type') == 'detailed':
                self.performance_monitor.update_stats('detailed_responses')
            
            return response_dict
            
        except Exception as e:
            self.logger.error(f"Error in enhanced RAG query: {e}", exc_info=True)
            fallback_response = self.response_formatter.format_fallback_response(university_x_id)
            return {
                "answer": fallback_response,
                "error": str(e),
                "university_x_id": university_x_id,
                "session_id": session_id,
                "lead_id": lead_id,
                "processing_time": time.time() - start_time
            }
    
    def _generate_response_with_context(self, question: str, doc_context: str, conversation_context: Dict,
                                      university_x_id: str, user_analysis: Dict, relevant_docs: List) -> Dict[str, Any]:
        """Generate response using LLM with proper context"""
        try:
            # Get university information
            from app.models.university import University
            university = University.get_university_by_x_id(university_x_id) if university_x_id else None
            university_name = university.get('name', 'our university') if university else 'our university'
            
            # Generate response using LLM client
            response_text = self.llm_client.generate_conversational_response(
                question, doc_context, conversation_context, university_name, user_analysis
            )
            
            # Apply user-type based formatting if needed
            user_name = conversation_context.get('user_info', {}).get('name', '')
            if user_analysis.get('education_level') != 'unknown':
                try:
                    formatted_response = self.user_analyzer.format_response_by_user_type(
                        response_text, user_analysis, user_name, university_name
                    )
                    response_text = formatted_response
                    self.logger.info(f"Applied {user_analysis.get('user_type', 'general')} formatting to response")
                except Exception as format_error:
                    self.logger.warning(f"Response formatting failed, using original: {format_error}")
            
            # Add source attribution
            final_response = self.response_formatter.add_source_attribution(response_text, relevant_docs)
            
            return {
                "answer": final_response,
                "conversation_aware": True,
                "university_branded": True,
                "user_personalized": bool(user_name),
                "response_type": "detailed" if len(doc_context) > 1000 else "standard",
                "university_name": university_name,
                "response_length": len(final_response),
                "topics": conversation_context.get('topics_discussed', []),
                "user_analysis": user_analysis,
                "background_filtered": user_analysis.get('education_level') != 'unknown',
                "user_type_formatted": user_analysis.get('education_level') != 'unknown'
            }
            
        except Exception as e:
            self.logger.error(f"Error generating response with context: {e}")
            fallback_response = self.response_formatter.format_fallback_response(university_x_id)
            return {
                "answer": fallback_response,
                "response_type": "fallback",
                "error": str(e)
            }
    
    def _is_greeting_or_simple(self, question: str) -> bool:
        """Check if the question is a greeting or simple response"""
        try:
            question_lower = question.lower().strip()
            
            # Remove common punctuation
            question_clean = re.sub(r'[.!?]+$', '', question_lower)
            
            # Greeting patterns
            greeting_patterns = [
                r'^(hi|hello|hey)(\s|$)',
                r'^(good\s+(morning|afternoon|evening))(\s|$)',
                r'^(thanks|thank\s+you)(\s|$)',
                r'^(bye|goodbye|see\s+you)(\s|$)',
                r'^(yes|yeah|yep|ok|okay)$',
                r'^(no|nope)$'
            ]
            
            for pattern in greeting_patterns:
                if re.match(pattern, question_clean):
                    return True
            
            # Check for very short responses (1-2 words)
            words = question_clean.split()
            if len(words) <= 2 and len(question_clean) <= 15:
                # But exclude potential names or longer meaningful words
                if not any(len(word) > 8 for word in words):
                    return True
            
            return False
        except Exception as e:
            self.logger.error(f"Error in greeting detection: {e}")
            return False
    
    def _should_skip_expensive_extraction(self, question: str, conversation_context: Dict) -> bool:
        """Conservative extraction filtering - defaults to NOT skipping"""
        try:
            # Always extract if smart filtering is disabled
            if not self.enable_smart_filtering:
                return False
        
            # Basic validation - only skip if message is invalid
            if not question or len(question.strip()) < 1:
                self.logger.debug("Skipping extraction - empty/invalid message")
                return True
        
            question_clean = question.strip()
            question_lower = question_clean.lower()
        
            # NEVER skip if personal information keywords are present
            personal_keywords_found = any(keyword in question_lower for keyword in self.personal_info_keywords)
            if personal_keywords_found:
                self.logger.debug(f"NOT skipping - found personal keywords in: '{question_clean}'")
                return False
        
            # NEVER skip if contains name introduction patterns
            name_intro_patterns = [
                r'\bmy name is\b', r'\bi\'m [a-zA-Z]', r'\bcall me\b', r'\bi am [a-zA-Z]',
                r'\bname is\b', r'\bhello.*i\'m\b', r'\bhi.*i\'m\b'
            ]
            for pattern in name_intro_patterns:
                if re.search(pattern, question_lower):
                    self.logger.debug(f"NOT skipping - found name pattern: {pattern}")
                    return False
        
            # NEVER skip if contains email patterns
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
            if re.search(email_pattern, question):
                self.logger.debug("NOT skipping - found email pattern")
                return False
        
            # NEVER skip if this is a response to a dynamic question
            if self.dynamic_questioner.is_response_to_dynamic_question(conversation_context):
                self.logger.debug("NOT skipping - response to dynamic question")
                return False
        
            # NEVER skip if message contains potential personal names
            if len(question_clean.split()) <= 3:  # Short messages that could be names
                words = question_clean.split()
                for word in words:
                    # Check if word looks like a name
                    if (word[0].isupper() and len(word) > 1 and len(word) <= 20 and 
                        word.isalpha() and word.lower() not in ['hi', 'hello', 'hey', 'yes', 'no', 'ok', 'thanks']):
                        self.logger.debug(f"NOT skipping - potential name detected: '{word}'")
                        return False
        
            # NEVER skip if message is longer (could contain personal info)
            if len(question_clean.split()) > 5:  # More than 5 words - likely contains info
                self.logger.debug(f"NOT skipping - longer message: {len(question_clean.split())} words")
                return False
        
            # ONLY skip for obvious non-personal cases
            obvious_skip_cases = [
                'what', 'how', 'when', 'where', 'why', 'which', 'who',
                'tell me about', 'information about', 'details about',
                'explain', 'describe', 'list', 'show me'
            ]
            
            if any(skip_phrase in question_lower for skip_phrase in obvious_skip_cases):
                self.logger.debug(f"Skipping extraction - obvious informational query: '{question_clean}'")
                return True
        
            # Default: don't skip (be conservative)
            self.logger.debug(f"NOT skipping extraction (conservative default): '{question_clean}'")
            return False
            
        except Exception as e:
            self.logger.error(f"Error in extraction filtering: {e}")
            return False  # Conservative: don't skip on errors
    
    def _is_simple_dynamic_response(self, question: str, conversation_context: Dict, lead_extracted: bool) -> bool:
        """Check if this is a simple response to a recent dynamic question"""
        return self.dynamic_questioner.is_simple_dynamic_response(question, conversation_context, lead_extracted)
    
    def _format_documents_for_response(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format documents for response metadata"""
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
    
    # Public API methods
    def get_rag_stats(self, university_code: str = None, university_x_id: str = None) -> Dict[str, Any]:
        """Get RAG service statistics for analytics"""
        try:
            stats = self.performance_monitor.get_rag_stats(university_x_id)
            
            # Update with component-specific information
            stats['service_info']['vector_search_available'] = self.vector_search_available
            stats['service_info']['main_model'] = self.main_model
            stats['service_info']['extraction_model'] = self.extraction_model
            stats['service_info']['cache_enabled'] = self.enable_response_cache
            stats['service_info']['smart_filtering_enabled'] = self.enable_smart_filtering
            
            # Add cache and session stats
            cache_stats = self.cache_manager.get_cache_stats()
            stats['performance_metrics']['cache_size'] = cache_stats['size']
            stats['performance_metrics']['active_sessions'] = self.session_state_manager.get_active_sessions_count()
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting RAG stats: {e}")
            return {"error": str(e)}
    
    def health_check(self) -> Tuple[bool, str]:
        """Check service health status"""
        try:
            # Check all components
            component_health = []
            
            # Check vector search
            vector_healthy, vector_msg = self.faiss_manager.health_check()
            component_health.append(('Vector Search', vector_healthy, vector_msg))
            
            # Check lead management
            lead_healthy, lead_msg = self.lead_extractor.health_check()
            component_health.append(('Lead Management', lead_healthy, lead_msg))
            
            # Check conversation management
            memory_healthy, memory_msg = self.memory_manager.health_check()
            component_health.append(('Memory Management', memory_healthy, memory_msg))
            
            # Check document search
            doc_healthy, doc_msg = self.document_finder.health_check()
            component_health.append(('Document Search', doc_healthy, doc_msg))
            
            # Check response generation
            response_healthy, response_msg = self.response_formatter.health_check()
            component_health.append(('Response Generation', response_healthy, response_msg))
            
            # Check questioning system
            question_healthy, question_msg = self.dynamic_questioner.health_check()
            component_health.append(('Questioning System', question_healthy, question_msg))
            
            # Check utilities
            cache_healthy, cache_msg = self.cache_manager.health_check()
            component_health.append(('Cache Manager', cache_healthy, cache_msg))
            
            perf_healthy, perf_msg = self.performance_monitor.health_check()
            component_health.append(('Performance Monitor', perf_healthy, perf_msg))
            
            # Overall health assessment
            all_healthy = all(health for _, health, _ in component_health)
            unhealthy_components = [name for name, health, _ in component_health if not health]
            
            if all_healthy:
                return True, "All Enhanced RAG components are healthy"
            else:
                return False, f"Unhealthy components: {', '.join(unhealthy_components)}"
                
        except Exception as e:
            return False, f"Health check failed: {e}"
    
    def clear_cache(self):
        """Clear response cache"""
        self.cache_manager.clear_cache()
    
    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get current state for a session"""
        return self.session_state_manager.get_session_state(session_id)
    
    def reset_session_state(self, session_id: str) -> bool:
        """Reset questioning state for a session"""
        return self.session_state_manager.reset_session_state(session_id)
    
    def clear_conversation_memory(self, session_id: str) -> bool:
        """Clear conversation memory for a session"""
        success = self.memory_manager.clear_conversation_memory(session_id)
        if success:
            self.session_state_manager.reset_session_state(session_id)
        return success
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of the conversation"""
        summary = self.memory_manager.get_conversation_summary(session_id)
        if 'enhanced_features_used' in summary:
            summary['enhanced_features_used']['vector_search'] = self.vector_search_available
            summary['enhanced_features_used']['dynamic_questioning'] = True
        summary['questioning_state'] = self.session_state_manager.get_session_state(session_id)
        return summary
    
    def update_stats(self, stat_name: str, increment: int = 1):
        """Update service statistics"""
        self.performance_monitor.update_stats(stat_name, increment)
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """Get comprehensive service metrics"""
        metrics = self.performance_monitor.get_service_metrics()
        if 'service_info' in metrics and 'capabilities' in metrics['service_info']:
            metrics['service_info']['capabilities']['vector_search'] = self.vector_search_available
        return metrics
    
    def optimize_performance(self):
        """Optimize service performance"""
        self.cache_manager.optimize_cache()
        self.performance_monitor.optimize_performance()
        self.session_state_manager.clean_expired_sessions()
