"""
Response formatter for Enhanced RAG Service
"""

import logging
from typing import Dict, List, Any
from app.models import universities_collection
from ..base.interfaces import ResponseGeneratorInterface


class ResponseFormatter(ResponseGeneratorInterface):
    """Handles response formatting and greeting generation"""
    
    def __init__(self):
        super().__init__()
    
    def generate_greeting_response(self, question: str, university_x_id: str, context: Dict) -> Dict[str, Any]:
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
    
    def generate_detailed_response(self, question: str, doc_context: str, conversation_context: Dict, 
                                 university_x_id: str = None, user_analysis: Dict = None) -> Dict[str, Any]:
        """This method is handled by LLMClient - keeping for interface compatibility"""
        return {
            "answer": "Response generation handled by LLM client",
            "response_type": "delegated"
        }
    
    def format_response_by_user_type(self, response_content: str, user_analysis: Dict[str, Any], 
                                   user_name: str = None, university_name: str = None) -> str:
        """This method is handled by UserAnalyzer - keeping for interface compatibility"""
        return response_content
    
    def add_source_attribution(self, response: str, relevant_docs: List[Dict[str, Any]]) -> str:
        """Add source attribution to response"""
        try:
            # Source attribution disabled for cleaner responses
            return response
            
            # COMMENTED OUT - Source attribution code
            # if not relevant_docs:
            #     return response
            # 
            # # Add source information if we have good matches
            # high_quality_docs = [doc for doc in relevant_docs if doc.get('metadata', {}).get('similarity_score', 0) > 10]
            # if high_quality_docs:
            #     sources = list(set([doc.get('source', 'university document') for doc in high_quality_docs[:2]]))
            #     source_info = f"\n\n*Information sourced from: {', '.join(sources)}*"
            #     return response + source_info
            # 
            # return response
            
        except Exception as e:
            self.logger.error(f"Error adding source attribution: {e}")
            return response
    
    def format_fallback_response(self, university_x_id: str = None) -> str:
        """Generate fallback response when AI processing fails"""
        try:
            from app.models.university import University
            university = University.get_university_by_x_id(university_x_id) if university_x_id else None
            university_name = university.get('name', 'our university') if university else 'our university'
            
            return f"I'm here to help you learn about {university_name}! I can assist with questions about our academic programs, admissions process, campus facilities, fees and scholarships, student life, and much more. What specific information would you like to know?"
        except Exception as e:
            self.logger.error(f"Error generating fallback response: {e}")
            return "I'm here to help you with information about our university programs and admissions. What would you like to know?"
    
    def format_documents_for_context(self, documents: List[Dict[str, Any]]) -> str:
        """Format documents for use in LLM context"""
        try:
            context_parts = []
            for i, doc in enumerate(documents):
                text = doc.get('text', '')
                source = doc.get('source', 'Unknown')
                
                # Limit individual document length
                if len(text) > 1500:
                    text = text[:1500] + "..."
                
                doc_entry = f"\n--- Document {i+1} (Source: {source}) ---\n{text}\n"
                context_parts.append(doc_entry)
                
                # Stop if context gets too long
                if len("".join(context_parts)) > 8000:
                    break
            
            return "".join(context_parts)
            
        except Exception as e:
            self.logger.error(f"Error formatting documents for context: {e}")
            return ""
    
    def health_check(self) -> tuple[bool, str]:
        """Check response formatter health"""
        try:
            # Test basic functionality
            test_response = self.generate_greeting_response("hello", None, {})
            if test_response and "answer" in test_response:
                return True, "Response formatter is healthy"
            else:
                return False, "Response formatter failed greeting test"
        except Exception as e:
            return False, f"Response formatter health check failed: {e}"
