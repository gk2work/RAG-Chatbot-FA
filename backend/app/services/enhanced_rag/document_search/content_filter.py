"""
Content filter for Enhanced RAG Service
"""

import logging
from typing import List, Dict, Any
from ..base.interfaces import BaseRAGComponent


class ContentFilter(BaseRAGComponent):
    """Handles content filtering and document relevance scoring"""
    
    def __init__(self):
        super().__init__()
    
    def filter_documents_by_relevance(self, documents: List[Dict[str, Any]], question: str, min_score: int = 5) -> List[Dict[str, Any]]:
        """Filter documents by relevance score"""
        try:
            filtered_docs = []
            for doc in documents:
                score = doc.get('metadata', {}).get('similarity_score', 0)
                if score >= min_score:
                    filtered_docs.append(doc)
            
            self.logger.debug(f"Filtered {len(documents)} documents to {len(filtered_docs)} based on relevance score >= {min_score}")
            return filtered_docs
            
        except Exception as e:
            self.logger.error(f"Error filtering documents by relevance: {e}")
            return documents
    
    def prioritize_high_quality_sources(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize documents from high-quality sources"""
        try:
            high_priority_keywords = ['course', 'program', 'curriculum', 'academic', 'admission']
            low_priority_keywords = ['general', 'misc', 'other']
            
            prioritized_docs = []
            
            for doc in documents:
                source = doc.get('source', '').lower()
                priority_score = 0
                
                # Boost high-quality sources
                if any(keyword in source for keyword in high_priority_keywords):
                    priority_score += 10
                
                # Reduce priority for low-quality sources
                if any(keyword in source for keyword in low_priority_keywords):
                    priority_score -= 5
                
                doc['metadata'] = doc.get('metadata', {})
                doc['metadata']['priority_score'] = priority_score
                prioritized_docs.append(doc)
            
            # Sort by priority score and existing similarity score
            prioritized_docs.sort(
                key=lambda x: (
                    x.get('metadata', {}).get('priority_score', 0),
                    x.get('metadata', {}).get('similarity_score', 0)
                ),
                reverse=True
            )
            
            return prioritized_docs
            
        except Exception as e:
            self.logger.error(f"Error prioritizing documents: {e}")
            return documents
    
    def deduplicate_documents(self, documents: List[Dict[str, Any]], similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Remove duplicate or very similar documents"""
        try:
            unique_docs = []
            seen_content = set()
            
            for doc in documents:
                text = doc.get('text', '')
                # Simple deduplication based on text content
                text_hash = hash(text.lower().strip())
                
                if text_hash not in seen_content:
                    seen_content.add(text_hash)
                    unique_docs.append(doc)
                else:
                    self.logger.debug(f"Skipped duplicate document from {doc.get('source', 'unknown')}")
            
            self.logger.debug(f"Deduplicated {len(documents)} documents to {len(unique_docs)}")
            return unique_docs
            
        except Exception as e:
            self.logger.error(f"Error deduplicating documents: {e}")
            return documents
    
    def format_documents_for_context(self, documents: List[Dict[str, Any]], max_context_length: int = 8000) -> str:
        """Format documents into context string with length control"""
        try:
            context_parts = []
            current_length = 0
            
            for i, doc in enumerate(documents):
                text = doc.get('text', '')
                source = doc.get('source', 'Unknown')
                
                # Format document entry
                doc_entry = f"\n--- Document {i+1} (Source: {source}) ---\n{text}\n"
                
                # Check if adding this document would exceed the limit
                if current_length + len(doc_entry) > max_context_length:
                    # Truncate the last document if needed
                    remaining_space = max_context_length - current_length
                    if remaining_space > 100:  # Only add if there's meaningful space
                        truncated_text = text[:remaining_space-50] + "..."
                        doc_entry = f"\n--- Document {i+1} (Source: {source}) [TRUNCATED] ---\n{truncated_text}\n"
                        context_parts.append(doc_entry)
                    break
                
                context_parts.append(doc_entry)
                current_length += len(doc_entry)
            
            context = "".join(context_parts)
            self.logger.debug(f"Formatted {len(context_parts)} documents into {len(context)} character context")
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error formatting documents for context: {e}")
            return ""
    
    def health_check(self) -> tuple[bool, str]:
        """Check content filter health"""
        try:
            # Test filtering functionality
            test_docs = [
                {
                    'text': 'test content',
                    'source': 'test.pdf',
                    'metadata': {'similarity_score': 10}
                },
                {
                    'text': 'low score content',
                    'source': 'test2.pdf',
                    'metadata': {'similarity_score': 2}
                }
            ]
            
            filtered = self.filter_documents_by_relevance(test_docs, "test", min_score=5)
            if len(filtered) == 1:
                return True, "Content filter is healthy"
            else:
                return False, "Content filter failed relevance test"
        except Exception as e:
            return False, f"Content filter health check failed: {e}"
