"""
Base interfaces and abstract classes for Enhanced RAG Service components
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
import logging


class BaseRAGComponent(ABC):
    """Base class for all RAG service components"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def health_check(self) -> Tuple[bool, str]:
        """Check component health status"""
        pass


class VectorSearchInterface(BaseRAGComponent):
    """Interface for vector search functionality"""
    
    @abstractmethod
    def find_relevant_documents_vector(self, question: str, university_x_id: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Find relevant documents using vector search"""
        pass
    
    @abstractmethod
    def load_faiss_index(self, university_x_id: str):
        """Load FAISS index for university"""
        pass


class LeadManagerInterface(BaseRAGComponent):
    """Interface for lead management functionality"""
    
    @abstractmethod
    def extract_and_manage_lead(self, question: str, session_id: str, lead_id: str, conversation_context: Dict) -> Tuple[bool, Dict[str, Any]]:
        """Extract and manage lead information"""
        pass
    
    @abstractmethod
    def analyze_educational_background(self, text: str) -> Dict[str, Any]:
        """Analyze user's educational background"""
        pass


class ConversationManagerInterface(BaseRAGComponent):
    """Interface for conversation management functionality"""
    
    @abstractmethod
    def get_conversation_context(self, session_id: str, lead_id: str = None) -> Dict:
        """Get conversation context"""
        pass
    
    @abstractmethod
    def update_conversation_memory(self, session_id: str, lead_id: str, question: str, response: Dict):
        """Update conversation memory"""
        pass
    
    @abstractmethod
    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get session state"""
        pass


class DocumentSearchInterface(BaseRAGComponent):
    """Interface for document search functionality"""
    
    @abstractmethod
    def get_university_documents(self, university_code: str = None, university_x_id: str = None) -> List[Dict[str, Any]]:
        """Get documents for university"""
        pass
    
    @abstractmethod
    def enhanced_document_search(self, question: str, documents: List[Dict[str, Any]], university_x_id: str = None) -> List[Dict[str, Any]]:
        """Enhanced document search with filtering"""
        pass
    
    @abstractmethod
    def filter_programs_by_background(self, documents: List[Dict[str, Any]], user_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter programs based on educational background"""
        pass


class ResponseGeneratorInterface(BaseRAGComponent):
    """Interface for response generation functionality"""
    
    @abstractmethod
    def generate_detailed_response(self, question: str, doc_context: str, conversation_context: Dict, university_x_id: str = None, user_analysis: Dict = None) -> Dict[str, Any]:
        """Generate detailed response"""
        pass
    
    @abstractmethod
    def generate_greeting_response(self, question: str, university_x_id: str, context: Dict) -> Dict[str, Any]:
        """Generate greeting response"""
        pass
    
    @abstractmethod
    def format_response_by_user_type(self, response_content: str, user_analysis: Dict[str, Any], user_name: str = None, university_name: str = None) -> str:
        """Format response based on user type"""
        pass


class QuestioningInterface(BaseRAGComponent):
    """Interface for dynamic questioning functionality"""
    
    @abstractmethod
    def get_dynamic_question(self, conversation_context: Dict, question: str, university_x_id: str = None) -> Optional[str]:
        """Get dynamic question"""
        pass
    
    @abstractmethod
    def is_response_to_dynamic_question(self, conversation_context: Dict) -> bool:
        """Check if response is to dynamic question"""
        pass
    
    @abstractmethod
    def get_next_sequential_question(self, user_info: Dict, session_state: Dict, conversation_length: int) -> Optional[Dict]:
        """Get next sequential question"""
        pass
