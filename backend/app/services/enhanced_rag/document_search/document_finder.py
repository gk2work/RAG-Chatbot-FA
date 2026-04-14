"""
Document finder for Enhanced RAG Service
"""

import logging
from typing import List, Dict, Any
from app.models import chunks_collection, universities_collection
from ..base.interfaces import DocumentSearchInterface


class DocumentFinder(DocumentSearchInterface):
    """Handles document retrieval and basic search functionality"""
    
    def __init__(self):
        super().__init__()
    
    def get_university_documents(self, university_code: str = None, university_x_id: str = None) -> List[Dict[str, Any]]:
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
            self.logger.error(f"Error in get_university_documents: {e}")
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
    
    def enhanced_document_search(self, question: str, documents: List[Dict[str, Any]], university_x_id: str = None) -> List[Dict[str, Any]]:
        """Enhanced document search with better keyword matching and scoring"""
        try:
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
    
    def filter_programs_by_background(self, documents: List[Dict[str, Any]], user_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """This method is implemented in UserAnalyzer - keeping for interface compatibility"""
        return documents
    
    def health_check(self) -> tuple[bool, str]:
        """Check document finder health"""
        try:
            # Test basic search functionality
            test_docs = [
                {'text': 'test program course', 'source': 'test.pdf'},
                {'text': 'another document', 'source': 'test2.pdf'}
            ]
            results = self.enhanced_document_search("program", test_docs)
            if len(results) > 0:
                return True, "Document finder is healthy"
            else:
                return False, "Document finder failed search test"
        except Exception as e:
            return False, f"Document finder health check failed: {e}"
