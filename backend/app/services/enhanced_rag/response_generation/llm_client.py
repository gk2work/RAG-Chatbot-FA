"""
LLM client wrapper for Enhanced RAG Service
"""

import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI
from app.config import Config
from ..base.interfaces import BaseRAGComponent


class LLMClient(BaseRAGComponent):
    """OpenAI client wrapper with optimizations and error handling"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Model configuration
        self.main_model = getattr(Config, 'OPENAI_MODEL', 'gpt-4o')
        self.extraction_model = getattr(Config, 'EXTRACTION_MODEL', 'gpt-3.5-turbo')
        self.temperature = getattr(Config, 'LLM_TEMPERATURE', 0.7)
        self.max_tokens = getattr(Config, 'MAX_TOKENS', 3000)
        self.extraction_max_tokens = 1500
        
        self.logger.info(f"LLM Client initialized - Main: {self.main_model}, Extraction: {self.extraction_model}")
    
    def generate_response(self, system_prompt: str, user_prompt: str, temperature: float = None, 
                         max_tokens: int = None, model: str = None) -> str:
        """Generate response using OpenAI API"""
        try:
            response = self.openai_client.chat.completions.create(
                model=model or self.main_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return "I'm having trouble processing your request right now. Please try again."
    
    def extract_information(self, text: str, extraction_prompt: str) -> Optional[str]:
        """Extract information using the extraction model"""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.extraction_model,
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.1,
                max_tokens=self.extraction_max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"Error in information extraction: {e}")
            return None
    
    def generate_detailed_response(self, question: str, doc_context: str, university_name: str, 
                                 user_name: str = "") -> str:
        """Generate detailed, document-based response for real queries"""
        try:
            system_prompt = f"""You are a friendly AI assistant for {university_name} that helps prospective students with admissions information through CONVERSATIONAL guidance.

            CRITICAL: FOLLOW USER REQUEST FORMAT EXACTLY:
            - If user asks to "list" something → Provide simple bullet-point list, no explanations
            - If user asks for "names" → Give only names requested
            - If user asks "tell me about" → Give brief overview
            - If user asks specific questions → Answer that specific question only

            CONVERSATION STYLE:
            1. Be conversational and personal, not encyclopedic
            2. Focus on answering the SPECIFIC question asked, not everything available
            3. Keep responses concise (2-4 key points maximum)
            4. Ask follow-up questions to understand what they really want to know
            5. Use the student's name ({user_name}) naturally in conversation
            6. Avoid overwhelming information dumps

            CONTENT GUIDELINES:
            7. Use ONLY the information provided in the university documents
            8. If they ask broadly (like "tell me about programs"), clarify what type they're interested in
            9. Provide specific details only when directly asked
            10. If specific info isn't available, acknowledge this briefly and offer related help
            11. End responses naturally without formal sign-offs
            
            REMEMBER: Have a conversation, don't write a brochure!
            """

            user_prompt = f"""Based on the university documents provided, please answer this student's question in a conversational way:

            UNIVERSITY DOCUMENTS:
            {doc_context}

            STUDENT QUESTION: {question}


            Respond conversationally - answer their specific question and ask a follow-up to understand what they really want to know. Keep it focused and friendly, not overwhelming
            CRITICAL: Analyze the user's request format:
            - If they want a "list" → Give bullet points or numbered list
            - If they want "names" → Give only names, no descriptions  
            - If they want explanation → Give brief explanation
            - Answer in the EXACT format they requested
            - If the specific information isn't in documents, say so clearly
            - Keep response 100-200 words maximum
            - Only ask follow-up if their request was unclear
            """
            
            return self.generate_response(system_prompt, user_prompt, temperature=0.3, max_tokens=300)
            
        except Exception as e:
            self.logger.error(f"Error generating detailed response: {e}")
            return f"Thank you for your question about {university_name}. I'd be happy to help you with detailed information about our programs, admissions, and facilities. Could you please let me know what specific aspect interests you most?"
    
    def generate_conversational_response(self, question: str, doc_context: str, conversation_context: Dict,
                                       university_name: str, user_analysis: Dict[str, Any] = None) -> str:
        """Generate conversational response focused on being helpful, not overwhelming"""
        try:
            user_info = conversation_context.get('user_info', {})
            user_name = user_info.get('name', '')
            
            # Build conversation history for context
            conv_history = ""
            if conversation_context.get('message_history'):
                recent_messages = conversation_context['message_history'][-3:]  # Last 3 messages for context
                conv_history = "\n".join([
                    f"{msg.get('role', 'user').upper()}: {msg.get('content', '')[:150]}" 
                    for msg in recent_messages
                ])
            
            # HELPFUL & CONVERSATIONAL system prompt - focus on being genuinely helpful but concise
            system_prompt = f"""You are a warm, helpful AI assistant for {university_name} that genuinely cares about helping prospective students with their educational journey.

            CONVERSATION STYLE - BE HUMAN & HELPFUL:
            1. Be genuinely helpful and encouraging - students are making important life decisions
            2. Answer their questions thoroughly but in a conversational way
            3. Provide helpful details when students ask specific questions - don't be overly brief
            4. Be warm and supportive, not robotic or dismissive
            5. Use the student's name ({user_name}) naturally when available
            6. Show enthusiasm about helping them achieve their educational goals
            7. Sound like a knowledgeable, friendly admissions counselor who wants to help

            CONTENT GUIDELINES:
            8. Use ONLY the information provided in the university documents
            9. When students ask for details, provide comprehensive information from the documents
            10. If specific info isn't available, acknowledge this and offer to help find related information
            11. Be encouraging about their educational journey and choices
            12. End responses in a way that invites further questions and shows you care
            
            REMEMBER: Students are trusting you with important educational decisions - be genuinely helpful, not dismissive!
            """

            # Add conversation context if available
            if conv_history:
                system_prompt += f"\n\nCONVERSATION CONTEXT:\nRecent conversation: {conv_history}"

            # HELPFUL & CONVERSATIONAL user prompt - emphasizing following user intent
            user_prompt = f"""Based on the university documents provided, please help this student with their question in a warm, conversational way:

            UNIVERSITY DOCUMENTS:
            {doc_context}

            STUDENT QUESTION: {question}
            Please provide a helpful, thorough response that addresses their question completely. Be conversational and encouraging, and include relevant details from the documents that would help them make informed decisions. Ask thoughtful follow-up questions to better understand how you can help them achieve their educational goals.
            CRITICAL INSTRUCTIONS:
            - Analyze what format the user is requesting (list, names, explanation, details)
            - If they ask to "list" → Provide bullet points or numbered list format
            - If they ask for "names" → Give only the names, no descriptions
            - If they ask "tell me about" → Give brief overview
            - Answer EXACTLY what they asked for, don't add unrequested information
            - If the specific information isn't in the documents, say so clearly
            - Keep response very concise (100-150 words max)
            - Only ask follow-up questions if the user's request was vague
            """
            
            return self.generate_response(system_prompt, user_prompt, temperature=0.3, max_tokens=250)
            
        except Exception as e:
            self.logger.error(f"Error generating conversational response: {e}")
            return f"Thank you for your question about {university_name}. I'd be happy to help you with information about our programs and services. How can I assist you further?"
    
    def health_check(self) -> tuple[bool, str]:
        """Check LLM client health"""
        try:
            # Test basic functionality
            test_response = self.generate_response(
                "You are a helpful assistant.",
                "Say 'test successful'",
                temperature=0,
                max_tokens=10
            )
            if "test successful" in test_response.lower():
                return True, "LLM client is healthy"
            else:
                return False, "LLM client failed test response"
        except Exception as e:
            return False, f"LLM client health check failed: {e}"
