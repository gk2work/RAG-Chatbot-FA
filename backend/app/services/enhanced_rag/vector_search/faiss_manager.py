"""
FAISS index management for Enhanced RAG Service
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from bson.objectid import ObjectId
from gridfs import GridFS
from pymongo import MongoClient

# Optional ML dependencies with graceful fallback
try:
    import faiss
    FAISS_SUPPORT = True
except ImportError:
    FAISS_SUPPORT = False
    faiss = None

from app.config import Config
from app.models import chunks_collection, universities_collection
from ..base.interfaces import VectorSearchInterface
from .embedding_service import EmbeddingService


class FAISSManager(VectorSearchInterface):
    """FAISS vector search manager for Enhanced RAG Service"""
    
    def __init__(self, embedding_service: EmbeddingService, fs: GridFS):
        super().__init__()
        self.embedding_service = embedding_service
        self.fs = fs
        self.vector_search_available = FAISS_SUPPORT and embedding_service.is_available()
        
        if not self.vector_search_available:
            self.logger.warning("FAISS support not available")
        else:
            self.logger.info("FAISS manager initialized successfully")
    
    def find_relevant_documents_vector(self, question: str, university_x_id: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Find relevant documents using FAISS vector search for the specific university_x_id."""
        try:
            if not self.vector_search_available:
                return []
                
            self.logger.debug(f"Vector search for university X-ID: {university_x_id}, question: {question[:100]}...")
            
            # Load FAISS index for this university
            index = self.load_faiss_index(university_x_id)
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
            query_embedding = self.embedding_service.encode_single(question)
            if query_embedding is None:
                self.logger.error("Failed to generate query embedding")
                return []
                
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

    def load_faiss_index(self, university_x_id: str):
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
            # Use debug level for missing files since it's expected in many cases
            if "no file in gridfs collection" in str(e):
                self.logger.debug(f"FAISS index not found for {university_x_id} - will use keyword search fallback")
            else:
                self.logger.error(f"Error loading FAISS index for {university_x_id}: {str(e)}")
            return None
    
    def health_check(self) -> Tuple[bool, str]:
        """Check FAISS manager health"""
        if not self.vector_search_available:
            return False, "FAISS support not available"
        
        # Check embedding service health
        embedding_healthy, embedding_msg = self.embedding_service.health_check()
        if not embedding_healthy:
            return False, f"Embedding service unhealthy: {embedding_msg}"
        
        return True, "FAISS manager is healthy"
