"""
Embedding service for Enhanced RAG Service
"""

import logging
import numpy as np
from typing import List, Optional

# Optional ML dependencies with graceful fallback
try:
    from sentence_transformers import SentenceTransformer
    VECTOR_SUPPORT = True
except ImportError:
    VECTOR_SUPPORT = False
    SentenceTransformer = None

from ..base.interfaces import BaseRAGComponent


class EmbeddingService(BaseRAGComponent):
    """Service for text embedding generation"""
    
    def __init__(self):
        super().__init__()
        self.embedder = None
        self.vector_search_available = False
        
        if VECTOR_SUPPORT:
            try:
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
                self.vector_search_available = True
                self.logger.info("Embedding service initialized with SentenceTransformer")
            except Exception as e:
                self.vector_search_available = False
                self.embedder = None
                self.logger.warning(f"Embedding service initialization failed: {e}")
        else:
            self.logger.info("Embedding service initialized without vector support (dependencies not available)")
    
    def encode(self, texts: List[str]) -> Optional[np.ndarray]:
        """Encode texts to embeddings"""
        if not self.vector_search_available or not self.embedder:
            self.logger.warning("Vector search not available for encoding")
            return None
            
        try:
            embeddings = self.embedder.encode(texts)
            return embeddings
        except Exception as e:
            self.logger.error(f"Error encoding texts: {e}")
            return None
    
    def encode_single(self, text: str) -> Optional[np.ndarray]:
        """Encode single text to embedding"""
        if not self.vector_search_available or not self.embedder:
            return None
            
        try:
            embedding = self.embedder.encode([text])[0].astype('float32')
            return embedding
        except Exception as e:
            self.logger.error(f"Error encoding single text: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if embedding service is available"""
        return self.vector_search_available and self.embedder is not None
    
    def health_check(self) -> tuple[bool, str]:
        """Check embedding service health"""
        if self.is_available():
            try:
                # Test encoding
                test_embedding = self.encode_single("test")
                if test_embedding is not None:
                    return True, "Embedding service is healthy"
                else:
                    return False, "Embedding service failed test encoding"
            except Exception as e:
                return False, f"Embedding service health check failed: {e}"
        else:
            return False, "Embedding service not available"
