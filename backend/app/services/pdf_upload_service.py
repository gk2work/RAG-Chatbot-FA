import logging
from pymongo import MongoClient
from bson.objectid import ObjectId
from gridfs import GridFS
from PyPDF2 import PdfReader
from io import BytesIO
from datetime import datetime
import os
from typing import Dict, Any, List
from app.config import Config
from app.models import chunks_collection, documents_collection, universities_collection

logger = logging.getLogger(__name__)

# Initialize MongoDB client and GridFS
client = MongoClient(Config.MONGODB_URI)
db = client[Config.MONGODB_DB_NAME]
fs = GridFS(db)

# Try to import FAISS and SentenceTransformers (optional for backward compatibility)
try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
    VECTOR_SUPPORT = True
    logger.info("Vector search capabilities enabled (FAISS + SentenceTransformers)")
except ImportError:
    VECTOR_SUPPORT = False
    logger.warning("Vector search disabled - install faiss-cpu and sentence-transformers for enhanced search")

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into chunks with overlap for better context preservation."""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        
        # Ensure we don't break words unless necessary
        if end < text_length and not text[end].isspace():
            # Find the last space to avoid breaking words
            last_space = chunk.rfind(' ')
            if last_space > start + chunk_size * 0.7:  # Don't make chunks too small
                end = start + last_space
                chunk = text[start:end]
        
        chunks.append(chunk.strip())
        start = end - overlap if end < text_length else end
    
    return [c for c in chunks if c]  # Remove empty chunks

def upload_pdf(university_x_id: str, file_data: bytes, filename: str) -> Dict[str, Any]:
    """
    Upload PDF to GridFS, create chunks, and optionally build FAISS index.
    
    This function integrates with the existing architecture while adding
    enhanced document processing capabilities.
    """
    try:
        # Validate university using existing X-ID system
        university = universities_collection.find_one({"x_id": university_x_id.upper()})
        if not university:
            logger.error(f"University with X-ID '{university_x_id}' not found")
            return {
                "success": False, 
                "error": f"University with X-ID '{university_x_id}' not found"
            }

        # Store PDF in GridFS with university-specific naming
        gridfs_filename = f"{university_x_id}_{filename}"
        file_id = fs.put(
            file_data, 
            filename=gridfs_filename, 
            metadata={
                "university_x_id": university_x_id,
                "original_filename": filename,
                "upload_type": "pdf_document",
                "created_at": datetime.utcnow()
            }
        )

        # Extract text from PDF
        pdf_stream = BytesIO(file_data)
        reader = PdfReader(pdf_stream)
        
        # Extract text from all pages
        text_content = ""
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                text_content += f"\n--- Page {page_num + 1} ---\n{page_text}"
            except Exception as page_error:
                logger.warning(f"Error extracting text from page {page_num + 1}: {page_error}")
                continue
        
        if not text_content.strip():
            logger.warning(f"No text extracted from {filename}")
            # Still store the document for potential manual processing
            text_content = f"[PDF Document: {filename} - Text extraction failed]"

        # Store document metadata in existing documents collection
        # This preserves compatibility with existing university model
        document_data = {
            "university_x_id": university_x_id.upper(),
            "university_code": university.get('code', '').lower(),  # Backward compatibility
            "title": filename,
            "content": text_content,  # Full text for existing systems
            "document_type": "pdf",
            "gridfs_file_id": str(file_id),  # NEW: GridFS reference
            "metadata": {
                "original_filename": filename,
                "file_size": len(file_data),
                "pages_count": len(reader.pages),
                "processing_method": "gridfs_chunked"
            },
            "created_at": datetime.utcnow()
        }
        
        doc_result = documents_collection.insert_one(document_data)
        document_id = str(doc_result.inserted_id)
        logger.info(f"Stored document {filename} with ID {document_id} for {university_x_id}")

        # Create text chunks for enhanced search
        chunks = chunk_text(text_content, 
                          chunk_size=getattr(Config, 'CHUNK_SIZE', 1000),
                          overlap=getattr(Config, 'CHUNK_OVERLAP', 200))
        
        # Store chunks in new chunks collection
        chunk_documents = []
        for i, chunk in enumerate(chunks):
            chunk_doc = {
                "university_x_id": university_x_id.upper(),
                "document_id": document_id,
                "file_id": str(file_id),
                "chunk_id": i + 1,
                "text": chunk,
                "metadata": {
                    "source_file": filename,
                    "chunk_size": len(chunk),
                    "total_chunks": len(chunks)
                },
                "created_at": datetime.utcnow()
            }
            chunk_documents.append(chunk_doc)
        
        if chunk_documents:
            chunks_collection.insert_many(chunk_documents)
            logger.info(f"Stored {len(chunks)} chunks for {filename}")

        # Update university document count (existing functionality)
        universities_collection.update_one(
            {"x_id": university_x_id.upper()},
            {"$inc": {"document_count": 1}}
        )

        # Build FAISS index if vector support is available
        faiss_success = False
        if VECTOR_SUPPORT:
            try:
                rebuild_faiss_index(university_x_id)
                faiss_success = True
                logger.info(f"FAISS index rebuilt successfully for {university_x_id}")
            except Exception as faiss_error:
                logger.warning(f"FAISS index rebuild failed for {university_x_id}: {faiss_error}")

        return {
            "success": True,
            "document_id": document_id,
            "file_id": str(file_id),
            "chunk_count": len(chunks),
            "vector_index_built": faiss_success,
            "pages_processed": len(reader.pages),
            "text_length": len(text_content)
        }
        
    except Exception as e:
        logger.error(f"Error uploading {filename} for {university_x_id}: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}

def rebuild_faiss_index(university_x_id: str) -> bool:
    """
    Rebuild FAISS index for a university and store it in GridFS.
    
    This function requires faiss-cpu and sentence-transformers to be installed.
    Falls back gracefully if not available.
    """
    if not VECTOR_SUPPORT:
        logger.warning("Vector search not available - skipping FAISS index rebuild")
        return False
        
    try:
        logger.info(f"Starting FAISS index rebuild for {university_x_id}")
        
        # Initialize embedding model
        embedder = SentenceTransformer('all-MiniLM-L6-v2')
        logger.debug("SentenceTransformer model loaded successfully")

        # Get all chunks for this university
        chunks = list(chunks_collection.find({"university_x_id": university_x_id.upper()}))
        if not chunks:
            logger.info(f"No chunks found for {university_x_id}")
            return False

        logger.debug(f"Found {len(chunks)} chunks for {university_x_id}")
        
        # Extract text and create embeddings
        texts = [chunk['text'] for chunk in chunks]
        chunk_ids = [str(chunk['_id']) for chunk in chunks]
        
        logger.debug(f"Encoding {len(texts)} text chunks")
        embeddings = embedder.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        logger.debug(f"Generated embeddings with shape {embeddings.shape}")

        # Create FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)  # L2 distance for similarity
        index.add(embeddings.astype('float32'))
        logger.debug(f"FAISS index created with {index.ntotal} vectors")

        # Serialize FAISS index
        index_bytes = faiss.serialize_index(index)
        if isinstance(index_bytes, np.ndarray):
            index_bytes = index_bytes.tobytes()
        
        # Create metadata for the index
        index_metadata = {
            "university_x_id": university_x_id.upper(),
            "chunk_count": len(chunks),
            "dimension": dimension,
            "chunk_ids": chunk_ids,  # Map index positions to chunk IDs
            "created_at": datetime.utcnow(),
            "model_name": "all-MiniLM-L6-v2"
        }

        # Remove old FAISS index if exists
        old_indexes = fs.find({"filename": f"{university_x_id}_faiss_index"})
        for old_index in old_indexes:
            fs.delete(old_index._id)
            logger.debug(f"Removed old FAISS index {old_index._id}")

        # Store new FAISS index in GridFS
        gridfs_filename = f"{university_x_id}_faiss_index"
        index_stream = BytesIO(index_bytes)
        faiss_file_id = fs.put(
            index_stream, 
            filename=gridfs_filename, 
            metadata=index_metadata
        )
        logger.debug(f"FAISS index stored in GridFS with ID {faiss_file_id}")

        # Update university document with FAISS index reference
        result = universities_collection.update_one(
            {"x_id": university_x_id.upper()},
            {"$set": {
                "gridfs_faiss_index": str(faiss_file_id),
                "vector_search_enabled": True,
                "last_index_update": datetime.utcnow()
            }}
        )
        
        if result.modified_count > 0:
            logger.info(f"Updated university {university_x_id} with FAISS index {faiss_file_id}")
            return True
        else:
            logger.warning(f"Failed to update university {university_x_id} with FAISS index")
            return False
            
    except Exception as e:
        logger.error(f"Error in rebuild_faiss_index for {university_x_id}: {str(e)}", exc_info=True)
        return False

def get_university_chunks(university_x_id: str) -> List[Dict[str, Any]]:
    """Get all text chunks for a university."""
    try:
        chunks = list(chunks_collection.find(
            {"university_x_id": university_x_id.upper()},
            {"text": 1, "metadata": 1, "document_id": 1, "chunk_id": 1, "university_x_id": 1}
        ).sort("created_at", -1))
        for chunk in chunks:
            if chunk.get("university_x_id") != university_x_id.upper():
                logger.error(f"ISOLATION BREACH: Found chunk with wrong X-ID: {chunk.get('university_x_id')}")
                
        return chunks
    except Exception as e:
        logger.error(f"Error getting chunks for {university_x_id}: {e}")
        return []

def search_chunks_vector(university_x_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search chunks using vector similarity (FAISS).
    Falls back to text search if vector search is unavailable.
    """
    if not VECTOR_SUPPORT:
        logger.debug("Vector search unavailable, falling back to text search")
        return search_chunks_text(university_x_id, query, top_k)
    
    try:
        # Get university and check if FAISS index exists
        university = universities_collection.find_one({"x_id": university_x_id.upper()})
        if not university or not university.get('gridfs_faiss_index'):
            logger.debug(f"No FAISS index found for {university_x_id}, falling back to text search")
            return search_chunks_text(university_x_id, query, top_k)

        # Load FAISS index from GridFS
        faiss_file_id = ObjectId(university['gridfs_faiss_index'])
        faiss_file = fs.get(faiss_file_id)
        index_bytes = faiss_file.read()
        
        # Deserialize FAISS index
        index = faiss.deserialize_index(np.frombuffer(index_bytes, dtype=np.uint8))
        
        # Get chunk mapping from metadata
        metadata = faiss_file.metadata or {}
        chunk_ids = metadata.get('chunk_ids', [])
        
        if len(chunk_ids) != index.ntotal:
            logger.warning(f"Chunk ID mapping mismatch for {university_x_id}")
            return search_chunks_text(university_x_id, query, top_k)

        # Encode query
        embedder = SentenceTransformer('all-MiniLM-L6-v2')
        query_embedding = embedder.encode([query], convert_to_numpy=True)
        
        # Search FAISS index
        distances, indices = index.search(query_embedding.astype('float32'), min(top_k, index.ntotal))
        
        # Get corresponding chunks
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx >= 0 and idx < len(chunk_ids):
                chunk_id = chunk_ids[idx]
                chunk = chunks_collection.find_one({"_id": ObjectId(chunk_id)})
                if chunk:
                    chunk['similarity_score'] = float(1 / (1 + distance))  # Convert distance to similarity
                    chunk['search_rank'] = i + 1
                    results.append(chunk)
        
        logger.debug(f"Vector search found {len(results)} results for query in {university_x_id}")
        return results
        
    except Exception as e:
        logger.error(f"Error in vector search for {university_x_id}: {e}")
        return search_chunks_text(university_x_id, query, top_k)

def search_chunks_text(university_x_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Fallback text-based search for chunks."""
    try:
        # Simple text search using MongoDB's text search capabilities
        chunks = list(chunks_collection.find(
            {
                "university_x_id": university_x_id.upper(),
                "text": {"$regex": query, "$options": "i"}  # Case-insensitive regex search
            },
            {"text": 1, "metadata": 1, "document_id": 1, "chunk_id": 1}
        ).limit(top_k))
        
        # Add simple relevance scoring based on query term frequency
        query_terms = query.lower().split()
        for chunk in chunks:
            text_lower = chunk['text'].lower()
            score = sum(text_lower.count(term) for term in query_terms)
            chunk['text_score'] = score
            chunk['search_method'] = 'text_regex'
        
        # Sort by relevance score
        chunks.sort(key=lambda x: x.get('text_score', 0), reverse=True)
        
        logger.debug(f"Text search found {len(chunks)} results for query in {university_x_id}")
        return chunks
        
    except Exception as e:
        logger.error(f"Error in text search for {university_x_id}: {e}")
        return []

def health_check() -> Dict[str, Any]:
    """Check the health of the PDF upload service."""
    try:
        # Test MongoDB connection
        db.command('ping')
        mongo_healthy = True
        mongo_message = "MongoDB connection successful"
    except Exception as e:
        mongo_healthy = False
        mongo_message = f"MongoDB connection failed: {e}"
    
    # Test GridFS
    try:
        fs.list()
        gridfs_healthy = True
        gridfs_message = "GridFS accessible"
    except Exception as e:
        gridfs_healthy = False
        gridfs_message = f"GridFS error: {e}"
    
    return {
        "service": "pdf_upload_service",
        "healthy": mongo_healthy and gridfs_healthy,
        "components": {
            "mongodb": {"healthy": mongo_healthy, "message": mongo_message},
            "gridfs": {"healthy": gridfs_healthy, "message": gridfs_message},
            "vector_search": {"available": VECTOR_SUPPORT, 
                            "message": "FAISS and SentenceTransformers available" if VECTOR_SUPPORT 
                                     else "Install faiss-cpu and sentence-transformers for vector search"}
        }
    } 
