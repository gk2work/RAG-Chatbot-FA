from flask import Blueprint, request, jsonify
from app.models.university import University
# Use simple RAG service to avoid LangChain compatibility issues
# from app.services.rag_service import RAGService
from app.services.pdf_upload_service import upload_pdf
from app.services.simple_rag_service import SimpleRAGService
from app.config import Config

import tempfile
import os
import base64
from werkzeug.utils import secure_filename
from app.utils.rbac import require_auth, require_admin_or_above, require_superadmin, Roles

university_bp = Blueprint('university', __name__)
# Use simple RAG service that completely bypasses LangChain
rag_service = SimpleRAGService()

@university_bp.route('/create', methods=['POST'])
@require_auth
@require_superadmin
def create_university():
    """Create a new university"""
    data = request.get_json()
    name = data.get('name')
    code = data.get('code')
    description = data.get('description', '')
    
    if not name or not code:
        return jsonify({"error": "Name and code are required"}), 400
    
    # Check if university already exists
    existing = University.get_university_by_code(code)
    if existing:
        return jsonify({"error": "University with this code already exists"}), 409
    
    university_id = University.create_university(name, code, description)
    
    # Get the created university to return X-ID
    university = University.get_university_by_code(code)
    
    return jsonify({
        "id": university_id,
        "x_id": university.get('x_id'),
        "message": f"University {name} created successfully"
    })

# @university_bp.route('/list', methods=['GET'])
# @require_auth
# @require_admin_or_above
# def list_universities():
#     """List universities based on user role and permissions"""
#     user_role = request.current_user.get('role')
    
#     if user_role == 'superadmin':
#         # SuperAdmin sees all universities
#         universities = University.get_all_universities()
#     elif user_role == 'admin':
#         # Admin sees only their assigned university
#         university_x_id = request.current_user.get('university_x_id')
        
#         if not university_x_id:
#             return jsonify({
#                 "error": "Admin user not assigned to any university",
#                 "universities": []
#             }), 403
        
#         # Get only the admin's assigned university
#         university = University.get_university_by_x_id(university_x_id)
#         if university:
#             universities = [university]
#         else:
#             return jsonify({
#                 "error": f"University with X-ID '{university_x_id}' not found",
#                 "universities": []
#             }), 404
#     else:
#         return jsonify({
#             "error": "Insufficient permissions to list universities",
#             "universities": []
#         }), 403
    
#     # Convert ObjectId to string (X-IDs are already included from model)
#     for uni in universities:
#         uni['_id'] = str(uni['_id'])
    
#     return jsonify({"universities": universities})

@university_bp.route('/list', methods=['GET'])
@require_auth
@require_admin_or_above
def list_universities():
    """List universities based on user role and permissions"""
    try:
        user_role = request.current_user.get('role')
        
        if user_role == 'superadmin':
            # SuperAdmin sees all universities
            universities = University.get_all_universities()
        elif user_role == 'admin':
            # Admin sees only their assigned university
            university_x_id = request.current_user.get('university_x_id')
            
            if not university_x_id:
                return jsonify({
                    "error": "Admin user not assigned to any university",
                    "universities": []
                }), 403
            
            # Get only the admin's assigned university
            university = University.get_university_by_x_id(university_x_id)
            if university:
                universities = [university]
            else:
                return jsonify({
                    "error": f"University with X-ID '{university_x_id}' not found",
                    "universities": []
                }), 404
        else:
            return jsonify({
                "error": "Insufficient permissions to list universities",
                "universities": []
            }), 403
        
        # ✅ CRITICAL FIX: Convert ALL ObjectIds to strings for JSON serialization
        for uni in universities:
            # Convert _id
            if '_id' in uni:
                uni['_id'] = str(uni['_id'])
            
            # Convert any other ObjectId fields that might exist
            if 'created_by' in uni and uni.get('created_by'):
                uni['created_by'] = str(uni['created_by'])
            if 'updated_by' in uni and uni.get('updated_by'):
                uni['updated_by'] = str(uni['updated_by'])
            if 'last_updated_by' in uni and uni.get('last_updated_by'):
                uni['last_updated_by'] = str(uni['last_updated_by'])
        
        return jsonify({"universities": universities})
        
    except Exception as e:
        
        return jsonify({
            "error": f"Failed to list universities: {str(e)}",
            "universities": []
        }), 500

@university_bp.route('/<x_id>', methods=['GET'])
@require_auth
@require_admin_or_above
def get_university_by_x_id(x_id):
    """Get university details by X-ID"""
    university = University.get_university_by_x_id(x_id)
    
    if not university:
        return jsonify({"error": "University not found"}), 404
    
    university['_id'] = str(university['_id'])
    
    documents = University.get_university_documents_by_x_id(x_id)
    
    return jsonify({
        "university": university,
        "x_id": university.get('x_id'),
        "document_count": len(documents)
    })

@university_bp.route('/<x_id>/documents', methods=['POST'])
@require_auth
@require_admin_or_above
def add_document(x_id):
    """
    Enhanced unified document upload endpoint supporting:
    - Text documents (legacy support)
    - Base64 encoded PDFs (new enhanced processing)
    - Automatic routing to appropriate processing service
    """
    data = request.get_json()
    
    title = data.get('title')
    content = data.get('content')
    doc_type = data.get('type', 'text')
    metadata = data.get('metadata', {})
    
    if not title or not content:
        return jsonify({"error": "Title and content are required"}), 400
    
    # Validate university exists
    university = University.get_university_by_x_id(x_id)
    if not university:
        return jsonify({"error": f"University with X-ID '{x_id}' not found"}), 404
    
    university_code = university['code']
    
    # Detect if content is base64 encoded PDF
    is_pdf_base64 = False
    if doc_type.lower() == 'pdf' or title.lower().endswith('.pdf'):
        try:
            # Try to decode base64 content to detect PDF
            import base64
            pdf_data = base64.b64decode(content)
            if pdf_data.startswith(b'%PDF'):  # PDF file signature
                is_pdf_base64 = True
                content_length = len(pdf_data)
        except Exception:
            # If decode fails, treat as text content
            content_length = len(str(content))
    else:
        content_length = len(str(content))
    
    # Validate document size
    max_size = getattr(Config, 'MAX_DOCUMENT_SIZE', 300000)  # Increased for PDFs
    if content_length > max_size:
        return jsonify({
            "error": f"Document too large: {content_length} bytes (maximum: {max_size})",
            "current_size": content_length,
            "max_size": max_size,
            "suggestion": "Please split your document into smaller parts or reduce content size"
        }), 413
    
    # Enhanced metadata for all document types
    document_metadata = {
        **metadata,
        "title": title,
        "original_size": content_length,
        "x_id": x_id,
        "processing_method": "enhanced_pdf" if is_pdf_base64 else "legacy_text",
        "upload_method": "api_json"
    }
    
    try:
        # Route to appropriate processing service
        if is_pdf_base64:
            # Use enhanced PDF processing service
            from app.services.pdf_upload_service import upload_pdf
            
            # Decode base64 PDF content
            pdf_data = base64.b64decode(content)
            filename = title if title.endswith('.pdf') else f"{title}.pdf"
            
            result = upload_pdf(x_id, pdf_data, filename)
            
            if result["success"]:
                return jsonify({
                    "message": "PDF document processed successfully with enhanced search capabilities",
                    "university_x_id": x_id,
                    "document_id": result.get("document_id"),
                    "file_id": result["file_id"],
                    "processing_method": "enhanced_pdf",
                    "processing_stats": {
                        "original_size": content_length,
                        "chunk_count": result["chunk_count"],
                        "pages_processed": result.get("pages_processed", 0),
                        "vector_index_built": result.get("vector_index_built", False),
                        "text_length": result.get("text_length", 0),
                        "processing_time": result.get("processing_time", 0)
                    }
                })
            else:
                return jsonify({
                    "error": result["error"],
                    "error_type": "pdf_processing_error",
                    "suggestion": "Please ensure the PDF is valid and try again"
                }), 500
        
        else:
            # Use legacy text processing for backward compatibility
            result = rag_service.process_document(university_code, content, doc_type, document_metadata)
            
            if not result.get('success', False):
                error_type = result.get('error_type', 'processing_error')
                error_message = result.get('error', 'Unknown processing error')
                
                return jsonify({
                    "error": error_message,
                    "error_type": error_type,
                    "suggestion": "Please check your document content and try again"
                }), 400 if error_type == 'validation_error' else 500
            
            # Store document in MongoDB database
            document_data = {
                "title": title,
                "content": content,
                "type": doc_type,
                "metadata": document_metadata
            }
            
            try:
                document_id = University.add_document_to_university(university_code, document_data)
            except Exception as db_error:
                import logging
                logging.warning(f"Database storage failed for document '{title}': {db_error}")
                document_id = None
            
            return jsonify({
                "message": "Text document processed successfully",
                "university_x_id": x_id,
                "document_id": document_id,
                "processing_method": "legacy_text",
                "processing_stats": {
                    "original_size": content_length,
                    "documents_added": result.get('documents_added', 0),
                    "processing_time": result.get('processing_time', 0),
                    "stats": result.get('stats', {}),
                    "database_stored": document_id is not None
                }
            })
    
    except ValueError as ve:
        return jsonify({
            "error": str(ve),
            "error_type": "validation_error",
            "suggestion": "Please check your document content and try again"
        }), 400
    
    except Exception as e:
        error_message = str(e)
        
        # Enhanced error handling
        if "memory" in error_message.lower():
            return jsonify({
                "error": "Document processing requires too much memory",
                "error_type": "memory_error",
                "suggestion": "Please try uploading a smaller document or contact support"
            }), 507
        elif "timeout" in error_message.lower():
            return jsonify({
                "error": "Document processing timed out",
                "error_type": "timeout_error", 
                "suggestion": "Please try again with a smaller document"
            }), 408
        elif "base64" in error_message.lower():
            return jsonify({
                "error": "Invalid base64 encoding in PDF content",
                "error_type": "encoding_error",
                "suggestion": "Please ensure PDF content is properly base64 encoded"
            }), 400
        else:
            return jsonify({
                "error": f"Failed to process document: {error_message}",
                "error_type": "processing_error",
                "suggestion": "Please try again or contact support if the issue persists"
            }), 500

@university_bp.route('/<x_id>/documents', methods=['GET'])
def get_university_documents(x_id):
    """
    Get all documents for a university by X-ID with enhanced metadata
    Shows processing method and capabilities for each document
    """
    university = University.get_university_by_x_id(x_id)
    if not university:
        return jsonify({"error": "University not found"}), 404
    
    # Get documents from MongoDB
    documents = University.get_university_documents_by_x_id(x_id)
    
    # Get enhanced document info if PDF service is available
    enhanced_info = {}
    try:
        from app.services.pdf_upload_service import get_university_chunks
        chunks = get_university_chunks(x_id)
        
        # Group chunks by document_id for quick lookup
        for chunk in chunks:
            doc_id = chunk.get('document_id')
            if doc_id not in enhanced_info:
                enhanced_info[doc_id] = {
                    'chunk_count': 0,
                    'total_text_length': 0,
                    'has_vector_search': True
                }
            enhanced_info[doc_id]['chunk_count'] += 1
            enhanced_info[doc_id]['total_text_length'] += len(chunk.get('text', ''))
    except ImportError:
        # PDF service not available
        pass
    except Exception as e:
        import logging
        logging.warning(f"Could not get enhanced document info: {e}")
    
    # Process documents for response
    processed_documents = []
    for doc in documents:
        doc_id = str(doc['_id'])
        doc['_id'] = doc_id
        
        # Remove large content for listing view but keep summary
        content = doc.pop('content', '')
        content_length = len(content)
        doc['content_preview'] = content[:200] + '...' if len(content) > 200 else content
        doc['content_length'] = content_length
        
        # Add processing method info
        metadata = doc.get('metadata', {})
        processing_method = metadata.get('processing_method', 'legacy_text')
        doc['processing_method'] = processing_method
        
        # Add enhanced capabilities info
        if doc_id in enhanced_info:
            doc['enhanced_capabilities'] = enhanced_info[doc_id]
            doc['search_type'] = 'vector_semantic'
        elif processing_method == 'enhanced_pdf':
            doc['search_type'] = 'enhanced_pdf'
        else:
            doc['search_type'] = 'keyword_text'
        
        # Add file size and type info
        doc['file_info'] = {
            'size_bytes': content_length,
            'size_readable': _format_file_size(content_length),
            'type': doc.get('document_type', doc.get('type', 'text')),
            'has_gridfs_file': bool(metadata.get('gridfs_file_id'))
        }
        
        processed_documents.append(doc)
    
    # Sort by creation date (newest first)
    processed_documents.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Calculate summary statistics
    total_documents = len(processed_documents)
    enhanced_count = sum(1 for doc in processed_documents 
                        if doc.get('processing_method') == 'enhanced_pdf' or 
                           doc.get('enhanced_capabilities'))
    total_size = sum(doc['content_length'] for doc in processed_documents)
    
    return jsonify({
        "university_x_id": x_id,
        "university_name": university.get('name'),
        "documents": processed_documents,
        "summary": {
            "total_documents": total_documents,
            "enhanced_documents": enhanced_count,
            "legacy_documents": total_documents - enhanced_count,
            "total_size_bytes": total_size,
            "total_size_readable": _format_file_size(total_size),
            "vector_search_available": enhanced_count > 0
        }
    })

def _format_file_size(size_bytes):
    """Helper function to format file size in human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
@university_bp.route('/<x_id>/upload_pdf', methods=['POST'])
@require_auth
@require_admin_or_above
def upload_pdf_route(x_id):
    x_id = x_id.upper()
    university = University.get_university_by_x_id(x_id)
    if not university:
        return jsonify({"error": f"University with X-ID '{x_id}' not found"}), 404

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = secure_filename(file.filename)
    if not filename.endswith('.pdf'):
        return jsonify({"error": "Only PDF files are supported"}), 400

    file_data = file.read()
    result = upload_pdf(x_id, file_data, filename)

    if result["success"]:
        return jsonify({
            "message": "PDF uploaded and processed successfully",
            "university_x_id": x_id,
            "file_id": result["file_id"],
            "chunk_count": result["chunk_count"]
        }), 200
    else:
        return jsonify({"error": result["error"]}), 500

@university_bp.route('/<x_id>/stats', methods=['GET'])
def get_university_stats(x_id):
    """Get comprehensive university statistics by X-ID"""
    # Get university by X-ID first
    university = University.get_university_by_x_id(x_id)
    if not university:
        return jsonify({"error": "University not found"}), 404
    
    # Get stats using the university code internally
    stats = University.get_university_stats(university['code'])
    
    if not stats:
        return jsonify({"error": "University statistics not found"}), 404
    
    # Convert ObjectId to string for recent documents
    for doc in stats['recent_documents']:
        doc['_id'] = str(doc['_id'])
    
    stats['university']['_id'] = str(stats['university']['_id'])
    
    return jsonify(stats)

@university_bp.route('/search', methods=['GET'])
def search_universities():
    """Search universities by name, code, or description"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({"error": "Search query is required"}), 400
    
    universities = University.search_universities(query)
    
    # Convert ObjectId to string
    for uni in universities:
        uni['_id'] = str(uni['_id'])
    
    return jsonify({
        "query": query,
        "results": universities,
        "count": len(universities)
    })

@university_bp.route('/<x_id>/documents/<document_id>', methods=['DELETE'])
def delete_document(x_id, document_id):
    """Delete a specific document by X-ID"""
    # Get university by X-ID to get the code for internal processing
    university = University.get_university_by_x_id(x_id)
    if not university:
        return jsonify({"error": "University not found"}), 404
    
    university_code = university['code']
    success = University.delete_document(document_id, university_code)
    
    if success:
        return jsonify({"message": "Document deleted successfully"})
    else:
        return jsonify({"error": "Document not found or could not be deleted"}), 404

# Legacy routes for backward compatibility (optional)
@university_bp.route('/code/<university_code>', methods=['GET'])
def get_university_by_code(university_code):
    """Get university details by code (legacy route)"""
    university = University.get_university_by_code(university_code)
    
    if not university:
        return jsonify({"error": "University not found"}), 404
    
    university['_id'] = str(university['_id'])
    
    documents = University.get_university_documents(university_code)
    
    return jsonify({
        "university": university,
        "x_id": university.get('x_id'),
        "document_count": len(documents)
    })

@university_bp.route('/code/<university_code>/documents', methods=['GET'])
def get_university_documents_by_code(university_code):
    """Get all documents for a university by code (legacy route)"""
    university = University.get_university_by_code(university_code)
    if not university:
        return jsonify({"error": "University not found"}), 404
    
    documents = University.get_university_documents(university_code)
    
    # Convert ObjectId to string and remove content for listing
    for doc in documents:
        doc['_id'] = str(doc['_id'])
        doc.pop('content', None)  # Remove content for listing view
    
    return jsonify({
        "university_x_id": university.get('x_id'),
        "documents": documents
    })

@university_bp.route('/<x_id>/search', methods=['GET'])
def search_university_documents(x_id):
    """
    Search documents within a university using enhanced search capabilities
    Supports both vector search and text search
    """
    query = request.args.get('q', '').strip()
    method = request.args.get('method', 'auto')  # auto, vector, text
    limit = min(int(request.args.get('limit', 10)), 50)  # Max 50 results
    
    if not query:
        return jsonify({"error": "Search query parameter 'q' is required"}), 400
    
    university = University.get_university_by_x_id(x_id)
    if not university:
        return jsonify({"error": "University not found"}), 404
    
    try:
        results = []
        search_method_used = "none"
        
        # Try enhanced vector search first if available and requested
        if method in ['auto', 'vector']:
            try:
                from app.services.pdf_upload_service import search_chunks_vector, search_chunks_text
                
                if method == 'vector' or method == 'auto':
                    vector_results = search_chunks_vector(x_id, query, limit)
                    if vector_results:
                        search_method_used = "vector_semantic"
                        for result in vector_results:
                            results.append({
                                'text': result.get('text', ''),
                                'source': result.get('metadata', {}).get('source_file', 'unknown'),
                                'similarity_score': result.get('similarity_score', 0),
                                'chunk_id': result.get('chunk_id', 0),
                                'document_id': result.get('document_id'),
                                'search_method': 'vector'
                            })
                
                # Fallback to text search if vector didn't return results
                if not results and method == 'auto':
                    text_results = search_chunks_text(x_id, query, limit)
                    if text_results:
                        search_method_used = "text_chunks"
                        for result in text_results:
                            results.append({
                                'text': result.get('text', ''),
                                'source': result.get('metadata', {}).get('source_file', 'unknown'),
                                'text_score': result.get('text_score', 0),
                                'chunk_id': result.get('chunk_id', 0),
                                'document_id': result.get('document_id'),
                                'search_method': 'text_chunks'
                            })
                            
            except ImportError:
                # Enhanced search not available, fall back to basic document search
                pass
        
        # Basic document text search if enhanced search not available or requested
        if not results and method in ['auto', 'text']:
            documents = University.get_university_documents_by_x_id(x_id)
            search_method_used = "basic_text"
            
            query_lower = query.lower()
            for doc in documents:
                content = doc.get('content', '')
                if query_lower in content.lower():
                    # Find context around the match
                    index = content.lower().find(query_lower)
                    start = max(0, index - 100)
                    end = min(len(content), index + len(query) + 100)
                    context = content[start:end]
                    
                    results.append({
                        'text': context,
                        'source': doc.get('title', 'unknown'),
                        'document_id': str(doc['_id']),
                        'match_position': index,
                        'search_method': 'basic_text'
                    })
                    
                    if len(results) >= limit:
                        break
        
        return jsonify({
            "university_x_id": x_id,
            "query": query,
            "search_method_used": search_method_used,
            "results": results[:limit],
            "total_results": len(results),
            "processing_time": "N/A"  # Could add timing if needed
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Search failed: {str(e)}",
            "university_x_id": x_id,
            "query": query
        }), 500

@university_bp.route('/<x_id>/rebuild-index', methods=['POST'])
@require_auth
@require_admin_or_above
def rebuild_university_index(x_id):
    """
    Rebuild the FAISS vector index for a university
    Useful when documents are added or updated
    """
    university = University.get_university_by_x_id(x_id)
    if not university:
        return jsonify({"error": "University not found"}), 404
    
    try:
        from app.services.pdf_upload_service import rebuild_faiss_index
        
        success = rebuild_faiss_index(x_id)
        
        if success:
            return jsonify({
                "message": f"Vector index rebuilt successfully for {university.get('name')}",
                "university_x_id": x_id,
                "index_rebuilt": True
            })
        else:
            return jsonify({
                "message": "Index rebuild completed but no chunks found or vector search not available",
                "university_x_id": x_id,
                "index_rebuilt": False
            }), 200
            
    except ImportError:
        return jsonify({
            "error": "Enhanced PDF service with vector search is not available",
            "suggestion": "Install faiss-cpu and sentence-transformers to enable vector search"
        }), 503
    except Exception as e:
        return jsonify({
            "error": f"Failed to rebuild index: {str(e)}",
            "university_x_id": x_id
        }), 500

@university_bp.route('/health', methods=['GET'])
def university_health_check():
    """
    Check the health of university-related services
    Including document processing capabilities
    """
    try:
        health_status = {
            "service": "university_routes",
            "healthy": True,
            "components": {}
        }
        
        # Test MongoDB connection
        try:
            University.get_university_count()
            health_status["components"]["mongodb"] = {
                "healthy": True,
                "message": "MongoDB connection successful"
            }
        except Exception as e:
            health_status["components"]["mongodb"] = {
                "healthy": False,
                "message": f"MongoDB error: {str(e)}"
            }
            health_status["healthy"] = False
        
        # Test Simple RAG Service
        try:
            rag_healthy, rag_message = rag_service.health_check()
            health_status["components"]["simple_rag"] = {
                "healthy": rag_healthy,
                "message": rag_message
            }
            if not rag_healthy:
                health_status["healthy"] = False
        except Exception as e:
            health_status["components"]["simple_rag"] = {
                "healthy": False,
                "message": f"Simple RAG error: {str(e)}"
            }
            health_status["healthy"] = False
        
        # Test Enhanced PDF Service
        try:
            from app.services.pdf_upload_service import health_check as pdf_health_check
            pdf_health = pdf_health_check()
            health_status["components"]["enhanced_pdf"] = pdf_health["components"]
            # Note: Don't fail overall health if enhanced PDF is unavailable
        except ImportError:
            health_status["components"]["enhanced_pdf"] = {
                "available": False,
                "message": "Enhanced PDF service not installed (optional)"
            }
        except Exception as e:
            health_status["components"]["enhanced_pdf"] = {
                "available": False,
                "message": f"Enhanced PDF service error: {str(e)}"
            }
        
        return jsonify(health_status), 200 if health_status["healthy"] else 503
        
    except Exception as e:
        return jsonify({
            "service": "university_routes",
            "healthy": False,
            "error": str(e)
        }), 503

@university_bp.route('/migrate-x-ids', methods=['POST'])
@require_auth
@require_superadmin
def migrate_x_ids():
    """Utility endpoint to add X-IDs to existing universities"""
    try:
        updated_count = University.ensure_x_ids_for_existing_universities()
        return jsonify({
            "message": f"Successfully added X-IDs to {updated_count} universities",
            "updated_count": updated_count
        })
    except Exception as e:
        return jsonify({"error": f"Migration failed: {str(e)}"}), 500
    

@university_bp.route('/<x_id>/branding', methods=['GET'])
def get_public_university_branding(x_id):
    """Get university branding information (public endpoint - no auth required)"""
    try:
        # Validate X-ID format
        if not x_id or len(x_id) < 8:
            return jsonify({"error": "Invalid university X-ID"}), 400
        
        # Get university branding data
        from app.models.university import University
        university_data = University.get_university_branding(x_id)
        
        if not university_data:
            return jsonify({"error": "University not found"}), 404
        
        # Flatten the structure for frontend consumption
        branding = university_data.get('branding', {})
        domains = university_data.get('domains', {})
        contact_info = university_data.get('contact_info', {})
        
        response_data = {
            "success": True,
            "university": {
                "name": university_data.get('name'),
                "code": university_data.get('code'),
                "x_id": university_data.get('x_id')
            },
            "branding": {
                # Logo & Visual Assets
                "logo_url": branding.get('logo_url', ''),
                "favicon_url": branding.get('favicon_url', ''),
                
                # Color Scheme
                "primary_color": branding.get('primary_color', '#1976d2'),
                "secondary_color": branding.get('secondary_color', '#424242'),
                "accent_color": branding.get('accent_color', '#ff4081'),
                
                # Typography & Theme
                "font_family": branding.get('font_family', 'Roboto, sans-serif'),
                "theme_name": branding.get('theme_name', 'default'),
                "custom_css": branding.get('custom_css', ''),
                
                # Domain Configuration
                "primary_domain": domains.get('primary_domain', ''),
                "subdomain": domains.get('subdomain', ''),
                "custom_domains": domains.get('custom_domains', []),
                
                # Contact Information
                "website_url": contact_info.get('website_url', ''),
                "support_email": contact_info.get('support_email', ''),
                "phone": contact_info.get('phone', ''),
                "address": contact_info.get('address', '')
            }
        }
        
        return jsonify(response_data)
    
    except Exception as e:
        print(f"Error getting public university branding: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500