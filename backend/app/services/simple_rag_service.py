

from openai import OpenAI
import logging
import time
import os
import json
import pickle
from typing import List, Dict, Any, Optional
from app.config import Config


class SimpleRAGService:
    """
    Simple RAG service using direct OpenAI API calls
    No LangChain dependencies to avoid compatibility issues
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # Initialize OpenAI client (new API format)
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = getattr(Config, 'OPENAI_MODEL', 'gpt-4o')
        self.temperature = getattr(Config, 'LLM_TEMPERATURE', 0.1)
        self.max_tokens = getattr(Config, 'MAX_TOKENS', 100000)

        self.logger.info("SimpleRAGService initialized successfully")

    def query(self, question: str, university_code: str, session_id: str = None, **kwargs) -> Dict[str, Any]:
        """Process a query using simple RAG without LangChain"""
        try:
            start_time = time.time()

            # Get documents for this university
            documents = self._get_university_documents(university_code)

            if not documents:
                return {
                    "answer": "I'm sorry, but I don't have access to information about this university.",
                    "source_documents": [],
                    "university_code": university_code,
                    "session_id": session_id,
                    "processing_time": time.time() - start_time
                }

            # Find relevant documents using simple keyword matching
            relevant_docs = self._find_relevant_documents(question, documents)

            # Create context from relevant documents
            context = "\n\n".join([doc.get('text', '') for doc in relevant_docs[:4]])

            # Generate response using OpenAI
            prompt = f"""You are a helpful university assistant. Use the following information to answer the question. If you don't know the answer, just say you don't know.

Context:
{context}

Question: {question}

Answer:"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            answer = response.choices[0].message.content
            processing_time = time.time() - start_time

            return {
                "answer": answer,
                "source_documents": self._format_documents(relevant_docs[:4]),
                "university_code": university_code,
                "session_id": session_id,
                "processing_time": processing_time
            }

        except Exception as e:
            self.logger.error(f"Error in simple RAG query: {e}")
            return {
                "answer": "I'm sorry, but I encountered an error while processing your question.",
                "source_documents": [],
                "university_code": university_code,
                "session_id": session_id,
                "error": str(e),
                "processing_time": time.time() - start_time if 'start_time' in locals() else 0
            }

    def _get_university_documents(self, university_code: str) -> List[Dict[str, Any]]:
        """Get documents for a university using simple file storage"""
        try:
            data_path = f"./data/universities/{university_code}"
            documents = []

            if os.path.exists(data_path):
                for filename in os.listdir(data_path):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(data_path, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            documents.append({
                                'text': content,
                                'source': filename,
                                'metadata': {'category': 'general', 'title': filename}
                            })

            self.logger.debug(f"Loaded {len(documents)} documents for {university_code}")
            return documents

        except Exception as e:
            self.logger.error(f"Error loading documents: {e}")
            return []

    def _find_relevant_documents(self, question: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find relevant documents using simple keyword matching"""
        try:
            question_lower = question.lower()

            scored_docs = []
            for doc in documents:
                text_lower = doc.get('text', '').lower()
                score = 0

                # Score based on keyword matches
                keywords = ['programs', 'courses', 'degree', 'bachelor', 'master', 'mba', 'undergraduate', 'postgraduate']
                for keyword in keywords:
                    if keyword in question_lower and keyword in text_lower:
                        score += 2

                question_words = question_lower.split()
                for word in question_words:
                    if len(word) > 3 and word in text_lower:
                        score += 1

                scored_docs.append((score, doc))

            scored_docs.sort(key=lambda x: x[0], reverse=True)
            return [doc for score, doc in scored_docs if score > 0]

        except Exception as e:
            self.logger.error(f"Error finding relevant documents: {e}")
            return documents

    def _format_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format documents for response"""
        formatted = []
        for i, doc in enumerate(documents):
            formatted.append({
                'chunk_text': doc.get('text', '')[:1000],
                'metadata': doc.get('metadata', {}),
                'chunk_index': i,
                'source': doc.get('source', 'unknown')
            })
        return formatted

    def health_check(self) -> tuple[bool, str]:
        """Check if the simple RAG service is healthy"""
        try:
            if not self.client.api_key:
                return False, "OpenAI API key not configured"
            return True, "Simple RAG service is healthy"
        except Exception as e:
            return False, f"Simple RAG service error: {str(e)}"

    def clear_conversation_memory(self, session_id: str) -> bool:
        """Placeholder for conversation memory (not implemented in simple version)"""
        return True

    def get_rag_stats(self, university_code: str) -> Dict[str, Any]:
        """Get simple RAG statistics"""
        try:
            documents = self._get_university_documents(university_code)
            return {
                "rag_config": {
                    "llm_model": self.model,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "service_type": "simple_rag"
                },
                "vectorstore_stats": {
                    "total_vectors": len(documents),
                    "university_code": university_code
                }
            }
        except Exception as e:
            return {"error": str(e)}
