from flask import Blueprint, request, jsonify
try:
    from app.services.enhanced_rag import EnhancedRAGService
    ENHANCED_RAG_IMPORT_SUCCESS = True
except ImportError as e:
    print(f"Warning: Could not import EnhancedRAGService: {e}")
    ENHANCED_RAG_IMPORT_SUCCESS = False
from app.services.simple_rag_service import SimpleRAGService
from app.models.chat import ChatSession
from app.utils.rbac import require_auth, require_admin_or_above, require_student_or_above, Roles
from app.models.university import University
from app.models.lead import Lead
from app.utils.rbac import require_auth, require_admin_or_above, Roles
from datetime import datetime
import logging
from bson import ObjectId 

chat_bp = Blueprint('chat', __name__)

# Initialize services with enhanced fallback support
try:
    enhanced_rag_service = EnhancedRAGService()
    simple_rag_service = SimpleRAGService()
    ENHANCED_RAG_AVAILABLE = True
    logging.info("Chat routes initialized with Enhanced RAG Service and Simple RAG fallback")
except Exception as e:
    simple_rag_service = SimpleRAGService()
    enhanced_rag_service = None
    ENHANCED_RAG_AVAILABLE = False
    logging.warning(f"Enhanced RAG Service unavailable, using Simple RAG only: {e}")


@chat_bp.route('/start', methods=['POST'])
@require_auth
def start_chat_session():
    """Start authenticated chat session with enhanced X-ID support"""
    data = request.get_json()
    university_x_id = data.get('university_x_id')
    university_code = data.get('university_code')  # Legacy support
    
    if not university_x_id and not university_code:
        return jsonify({"error": "university_x_id or university_code is required"}), 400

    try:
        # Get university information using helper function
        university, resolved_university_code = _get_university_info(university_code, university_x_id)
        if not university:
            return jsonify({"error": "University not found"}), 404
        
        # Create session using appropriate method
        if university_x_id:
            session_id = ChatSession.create_session_by_x_id(university_x_id, request.current_user['id'])
        else:
            session_id = ChatSession.create_session(resolved_university_code, request.current_user['id'])
        
        session = ChatSession.get_session(session_id)
        
        # Generate personalized welcome message
        user_name = request.current_user.get('name', 'there')
        welcome_message = _generate_welcome_message(
            university, resolved_university_code, session_id, user_name=user_name
        )
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "university_x_id": university.get('x_id'),
            "university_name": university.get('name'),
            "welcome_message": welcome_message,
            "user_role": request.current_user['role'],
            "enhanced_features": {
                "conversational_memory": ENHANCED_RAG_AVAILABLE,
                "lead_management": ENHANCED_RAG_AVAILABLE,
                "dynamic_questioning": ENHANCED_RAG_AVAILABLE
            }
        })
    except Exception as e:
        logging.error(f"Error starting chat session: {str(e)}")
        return jsonify({"error": f"Failed to create session: {str(e)}"}), 500

@chat_bp.route('/message', methods=['POST'])
@require_auth
def send_message():
    """Send message in authenticated session with enhanced processing"""
    data = request.get_json()
    session_id = data.get('session_id')
    message = data.get('message')

    if not session_id or not message:
        return jsonify({"error": "Session ID and message are required"}), 400

    session = ChatSession.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    # Verify session ownership
    if str(session.get('user_id')) != str(request.current_user['id']):
        return jsonify({"error": "Access denied"}), 403

    university_code = session.get('university_code')
    university_x_id = session.get('university_x_id')
    
    if not university_code:
        return jsonify({"error": "University information not found in session"}), 400

    try:
        # Process message with enhanced RAG
        response, metadata = _process_rag_query(
            message, university_code, session_id, is_public=False, university_x_id=university_x_id
        )
        
        # Store assistant response
        ChatSession.add_message(session_id, "assistant", response, metadata)
        
        # Enhanced response with additional context
        return jsonify({
            "success": True,
            "response": response,
            "metadata": {
                **metadata,
                "session_id": session_id,
                "university_x_id": university_x_id,
                "enhanced_rag_used": ENHANCED_RAG_AVAILABLE
            }
        })
        
    except Exception as e:
        logging.error(f"Error processing message: {str(e)}")
        return jsonify({"error": f"Failed to process message: {str(e)}"}), 500

@chat_bp.route('/public-message', methods=['POST'])
def send_public_message():
    """Send a message in public session (no authentication required)"""
    data = request.get_json()
    session_id = data.get('session_id')
    message = data.get('message')
    lead_id = data.get('lead_id')  # Optional lead ID
    
    if not session_id or not message:
        return jsonify({
            "success": False,
            "error": "Session ID and message are required"
        }), 400
    
    # Get session (public sessions don't need user verification)
    from app.models import chat_sessions_collection
    from bson import ObjectId
    
    try:
        session = chat_sessions_collection.find_one({"_id": ObjectId(session_id)})
        if not session:
            return jsonify({
                "success": False,
                "error": "Session not found"
            }), 404
        
        university_code = session['university_code']
        university_x_id = session.get('university_x_id')  # Get X-ID from session
        
        # If no lead_id provided, check if this session already has an associated lead
        if not lead_id:
            existing_lead_id = session.get('lead_id')
            if existing_lead_id:
                lead_id = existing_lead_id
                logging.info(f"Found existing lead {lead_id} for session {session_id}")
        
        # Process RAG query using helper function
        response, enhanced_metadata = _process_rag_query(
            message, university_code, session_id, lead_id, is_public=True, university_x_id=university_x_id
        )

        # ✅ FIXED: Handle lead creation from Enhanced RAG extraction
        original_lead_id = lead_id
        extracted_lead_id = enhanced_metadata.get('lead_id')
        lead_created_during_chat = False
        lead_updated_during_chat = False

         # Check if Enhanced RAG created or found a lead
        if extracted_lead_id and extracted_lead_id != original_lead_id:
            if not original_lead_id:
                # New lead was created during conversation
                lead_id = extracted_lead_id
                lead_created_during_chat = True
                
                # ✅ FIXED: Link the session to the newly created lead
                try:
                    from app.models import chat_sessions_collection
                    chat_sessions_collection.update_one(
                        {"_id": ObjectId(session_id)},
                        {"$set": {"lead_id": lead_id, "updated_at": datetime.utcnow()}}
                    )
                    # Also link the lead to the session
                    Lead.add_chat_session(lead_id, session_id)
                    
                    logging.info(f"✅ NEW LEAD {lead_id} created during public chat and linked to session {session_id}")
                    
                except Exception as link_error:
                    logging.error(f"Failed to link new lead {lead_id} to session {session_id}: {link_error}")
                    
            else:
                # Existing lead was updated
                lead_id = extracted_lead_id
                lead_updated_during_chat = True
                logging.info(f"✅ Lead {lead_id} updated during public chat (was {original_lead_id})")
        
        # ✅ FIXED: Fallback lead creation for partial information
        elif not lead_id and ENHANCED_RAG_AVAILABLE:
            # Try to extract basic information for minimal lead creation
            try:
                conversation_context = enhanced_metadata.get('conversation_context', {})
                user_name = enhanced_metadata.get('user_name')
                
                # Check if we have enough info for a minimal lead
                if user_name or len(message.split()) > 10:  # Long message might contain personal info
                    # ✅ FIXED: Create minimal lead for tracking purposes
                    minimal_lead_id, is_existing = Lead.create_lead(
                        name=user_name or "Chat User",
                        email="",  # Will be filled later if provided
                        university_code=university_code,
                        country="Unknown"  # Will be filled later if provided
                    )
                    if minimal_lead_id:
                        lead_id = minimal_lead_id
                        lead_created_during_chat = True
                        
                        # Link session and lead
                        chat_sessions_collection.update_one(
                            {"_id": ObjectId(session_id)},
                            {"$set": {"lead_id": lead_id, "updated_at": datetime.utcnow()}}
                        )
                        Lead.add_chat_session(lead_id, session_id)
                        
                        logging.info(f"✅ Created minimal lead {lead_id} for tracking in session {session_id}")
                        
            except Exception as fallback_error:
                logging.warning(f"Fallback lead creation failed: {fallback_error}")
        
        # Add additional metadata for public sessions
        enhanced_metadata.update({
            "university_x_id": session.get('university_x_id'),
            "session_id": session_id,
             "lead_created": enhanced_metadata.get('lead_created', False) or lead_created_during_chat,
            "lead_updated": enhanced_metadata.get('lead_updated', False) or lead_updated_during_chat,
            "partial_lead_created": enhanced_metadata.get('partial_lead_created', False),
            "is_public_session": True,
            "original_lead_id": original_lead_id,
            "final_lead_id": lead_id
        })
        
        return jsonify({
            "success": True,
            "response": response,
            "metadata": enhanced_metadata,
            "lead_id": lead_id,  # ✅ FIXED: Return current lead_id (might be newly created)
            "lead_created": lead_created_during_chat,  # ✅ FIXED: Inform frontend about lead creation
            "session_linked_to_lead": bool(lead_id)  # ✅ FIXED: Indicate if session is now linked
        })
    
    except Exception as e:
        logging.error(f"Error in public message: {str(e)}")
        error_response = f"I apologize, but I encountered an error while processing your question: {str(e)}"
        error_metadata = {
            "error": True,
            "university_x_id": session.get('university_x_id') if 'session' in locals() else None,
            "session_id": session_id,
            "rag_approach": "enhanced_conversational",
            "error_message": str(e),
            "is_public_session": True
        }
        
        return jsonify({
            "success": True,  # Still return success to keep conversation flowing
            "response": error_response,
            "metadata": error_metadata
        })

@chat_bp.route('/start-public-session', methods=['POST'])
def start_public_enhanced_session():
    """Start a new public chat session with enhanced memory (no authentication required)"""
    data = request.get_json()
    lead_name = data.get('name')
    lead_email = data.get('email')
    lead_country = data.get('country')
    lead_mobile = data.get('mobile')
    university_code = data.get('university_code', 'csss')
    university_x_id = data.get('university_x_id')
    
    # For public sessions, we'll create a minimal session first, then enhance as conversation progresses
    try:
        # Get university information using helper function
        university, university_code = _get_university_info(university_code, university_x_id)
        if not university:
            return jsonify({"error": "University not found"}), 404
        
        # Create a public session (no user_id required)
        session_data = {
            "university_code": university_code.lower(),
            "university_x_id": university.get('x_id'),
            "university_name": university.get('name'),
            "user_id": None,  # Public session
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True,
            "message_count": 0,
            "is_public": True
        }
        
        from app.models import chat_sessions_collection
        result = chat_sessions_collection.insert_one(session_data)
        session_id = str(result.inserted_id)
        
       # ✅ FIXED: More flexible lead creation - don't require ALL fields
        lead_id = None
        is_existing_lead = False
        
        # Create lead if we have at least name OR email
        if lead_name or lead_email:
            try:
                # ✅ FIXED: Create lead with available information
                lead_id, is_existing_lead = Lead.create_lead(
                    name=lead_name or "Anonymous User",  # Default name if not provided
                    email=lead_email or "",              # Empty email if not provided
                    university_code=university_code,
                    country=lead_country or "Unknown",   # Default country if not provided
                    mobile=lead_mobile or ""             # Empty mobile if not provided
                )
                
                # Link session to lead
                Lead.add_chat_session(lead_id, session_id)
                
                # ✅ FIXED: Update session with lead_id for future reference
                from app.models import chat_sessions_collection
                chat_sessions_collection.update_one(
                    {"_id": ObjectId(session_id)},
                    {"$set": {"lead_id": lead_id, "updated_at": datetime.utcnow()}}
                )
                
                logging.info(f"✅ Created lead {lead_id} for public session {session_id} with name='{lead_name}', email='{lead_email}'")
                
            except Exception as lead_error:
                logging.warning(f"Failed to create lead in public session: {lead_error}")
        else:
            logging.debug(f"No lead info provided for public session {session_id}, will extract during conversation")
        
        # Generate personalized welcome message using helper function
        welcome_message = _generate_welcome_message(
            university, university_code, session_id, lead_id, lead_name
        )
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "lead_id": lead_id,
            "is_existing_lead": is_existing_lead,
            "university": university['name'],
            "university_code": university['code'],
            "university_x_id": university.get('x_id'),
            "welcome_message": welcome_message,
            "conversation_memory_enabled": ENHANCED_RAG_AVAILABLE,
            "dynamic_questioning_enabled": ENHANCED_RAG_AVAILABLE,
            "enhanced_features": {
                "lead_tracking": bool(lead_id),
                "personalized_responses": bool(lead_name),
                "university_branding": bool(university.get('branding'))
            }
        })
        
    except Exception as e:
        logging.error(f"Error starting public session: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to create public session: {str(e)}"
        }), 500

@chat_bp.route('/history/<session_id>', methods=['GET'])
@require_auth
def get_chat_history(session_id):
    """Get chat history for a session - requires authentication"""
    session = ChatSession.get_session(session_id)
    
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    # Verify user owns this session
    if str(session.get('user_id')) != str(request.current_user['id']):
        return jsonify({"error": "Access denied. You can only view your own chat history."}), 403
    
    messages = ChatSession.get_session_messages(session_id)
    
    # Include enhanced session info with X-ID
    session_info = {
        "university_code": session.get('university_code'),
        "university_x_id": session.get('university_x_id'),
        "university_name": session.get('university_name'),
        "created_at": session.get('created_at'),
        "user_id": session.get('user_id'),
        "message_count": session.get('message_count', len(messages)),
        "is_active": session.get('is_active', True)
    }
    
    return jsonify({
        "success": True,
        "messages": messages,
        "session_info": session_info,
        "enhanced_features_used": ENHANCED_RAG_AVAILABLE
    })

@chat_bp.route('/sessions/user/<user_id>', methods=['GET'])
@require_auth
def get_user_sessions(user_id):
    """Get all chat sessions for a user - requires authentication"""
    try:
        # Users can only view their own sessions, admins can view any user's sessions
        if request.current_user['role'] == 'student' and str(request.current_user['id']) != str(user_id):
            return jsonify({"error": "Students can only view their own sessions"}), 403
        
        limit = int(request.args.get('limit', 10))
        sessions = ChatSession.get_sessions_by_user(user_id, limit)
        
        # Convert ObjectId to string and remove messages for listing
        for session in sessions:
            session['_id'] = str(session['_id'])
            session.pop('messages', None)
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "sessions": sessions,
            "count": len(sessions)
        })
    except Exception as e:
        logging.error(f"Error getting user sessions: {str(e)}")
        return jsonify({"error": f"Failed to get user sessions: {str(e)}"}), 500

@chat_bp.route('/sessions/university/<university_identifier>', methods=['GET'])
@require_auth
@require_admin_or_above
def get_university_sessions(university_identifier):
    """Get recent chat sessions for a university (by code or X-ID) - requires admin access"""
    try:
        limit = int(request.args.get('limit', 10))
        
        # Check if it's an X-ID (starts with 'X') or university code
        if university_identifier.startswith('X'):
            sessions = ChatSession.get_sessions_by_university_x_id(university_identifier, limit)
        else:
            sessions = ChatSession.get_sessions_by_university_code(university_identifier, limit)
        
        # Convert ObjectId to string and remove messages
        for session in sessions:
            session['_id'] = str(session['_id'])
            session.pop('messages', None)
        
        return jsonify({
            "success": True,
            "university_identifier": university_identifier,
            "sessions": sessions,
            "count": len(sessions)
        })
    except Exception as e:
        logging.error(f"Error getting university sessions: {str(e)}")
        return jsonify({"error": f"Failed to get university sessions: {str(e)}"}), 500

@chat_bp.route('/session/<session_id>/summary', methods=['GET'])
@require_auth
def get_session_summary(session_id):
    """Get a summary of a chat session - requires authentication"""
    try:
        # Verify user owns this session or is admin
        session = ChatSession.get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        # Allow admins to view any session summary
        if (request.current_user['role'] not in ['admin', 'superadmin'] and 
            str(session.get('user_id')) != str(request.current_user['id'])):
            return jsonify({"error": "Access denied"}), 403
        
        summary = ChatSession.get_session_summary(session_id)
        
        if not summary:
            return jsonify({"error": "Session summary not available"}), 404
        
        return jsonify({
            "success": True,
            "summary": summary
        })
    except Exception as e:
        logging.error(f"Error getting session summary: {str(e)}")
        return jsonify({"error": f"Failed to get session summary: {str(e)}"}), 500

@chat_bp.route('/health', methods=['GET'])
def chat_service_health():
    """Check health of chat services and dependencies"""
    try:
        health_status = {
            "service": "chat_routes",
            "healthy": True,
            "components": {}
        }
        
        # Test Enhanced RAG Service
        if ENHANCED_RAG_AVAILABLE and enhanced_rag_service:
            try:
                rag_healthy, rag_message = enhanced_rag_service.health_check()
                health_status["components"]["enhanced_rag"] = {
                    "healthy": rag_healthy,
                    "message": rag_message
                }
                if not rag_healthy:
                    health_status["healthy"] = False
            except Exception as e:
                health_status["components"]["enhanced_rag"] = {
                    "healthy": False,
                    "message": f"Enhanced RAG error: {str(e)}"
                }
                health_status["healthy"] = False
        
        # Test Simple RAG Service
        try:
            simple_healthy, simple_message = simple_rag_service.health_check()
            health_status["components"]["simple_rag"] = {
                "healthy": simple_healthy,
                "message": simple_message
            }
            if not simple_healthy:
                health_status["healthy"] = False
        except Exception as e:
            health_status["components"]["simple_rag"] = {
                "healthy": False,
                "message": f"Simple RAG error: {str(e)}"
            }
            health_status["healthy"] = False
        
        # Test Chat Session model
        try:
            ChatSession.get_sessions_created_today()
            health_status["components"]["chat_sessions"] = {
                "healthy": True,
                "message": "Chat sessions operational"
            }
        except Exception as e:
            health_status["components"]["chat_sessions"] = {
                "healthy": False,
                "message": f"Chat sessions error: {str(e)}"
            }
            health_status["healthy"] = False
        
        # Add service capabilities
        health_status["capabilities"] = {
            "enhanced_rag_available": ENHANCED_RAG_AVAILABLE,
            "public_sessions": True,
            "x_id_support": True,
            "lead_integration": True,
            "conversational_memory": ENHANCED_RAG_AVAILABLE
        }
        
        return jsonify(health_status), 200 if health_status["healthy"] else 503
        
    except Exception as e:
        return jsonify({
            "service": "chat_routes",
            "healthy": False,
            "error": str(e)
        }), 503

# Helper functions to reduce code duplication
def _get_university_info(university_code=None, university_x_id=None):
    """Helper function to get university info by code or X-ID"""
    try:
        if university_x_id:
            university = University.get_university_by_x_id(university_x_id)
            university_code = university['code'] if university else university_code
        else:
            university = University.get_university_by_code(university_code)
        return university, university_code
    except Exception as e:
        logging.error(f"Error getting university info: {str(e)}")
        return None, university_code

def _generate_welcome_message(university, university_code, session_id, lead_id=None, lead_name=None, user_name=None):
    """Helper function to generate personalized welcome messages"""
    try:
        # Use lead_name or user_name for personalization
        person_name = lead_name or user_name
        university_name = university.get('name', 'our university')
        
        if ENHANCED_RAG_AVAILABLE and enhanced_rag_service:
            # Use enhanced RAG for dynamic welcome messages
            if person_name:
                welcome_prompt = f"Generate a brief, friendly welcome message for {person_name} visiting {university_name}"
            else:
                welcome_prompt = f"Generate a brief, friendly welcome message for someone visiting {university_name}"
            
            welcome_response = enhanced_rag_service.query(
                question=welcome_prompt,
                university_code=university_code,
                session_id=session_id,
                lead_id=lead_id,
                is_first_message=True
            )
            
            return welcome_response.get('answer', _get_fallback_welcome(person_name, university_name))
        else:
            return _get_fallback_welcome(person_name, university_name)
            
    except Exception as e:
        logging.warning(f"Error generating welcome message: {str(e)}")
        return _get_fallback_welcome(lead_name or user_name, university.get('name', 'our university'))

def _get_fallback_welcome(person_name, university_name):
    """Generate a fallback welcome message"""
    if person_name:
        return f"Hi {person_name}! Welcome to {university_name}! 🎓 I'm here to help you with information about our programs, admissions, and facilities. How can I assist you today?"
    else:
        return f"Welcome to {university_name}! 🎓 I'm your AI assistant, ready to help you with information about our programs, admissions, facilities, and answer any questions you might have. How can I assist you today?"

def _process_rag_query(message, university_code, session_id, lead_id=None, is_public=False, university_x_id=None):
    """Helper function to process RAG queries with enhanced fallback and COMPLETE lead management"""
    try:
        # Store user message first with enhanced metadata
        user_message_metadata = {
            "is_public_session": is_public,
            "lead_id": lead_id,
            "processing_method": "enhanced_rag" if ENHANCED_RAG_AVAILABLE else "simple_rag",
            "university_x_id": university_x_id,
            "timestamp": datetime.utcnow()
        }
        
        ChatSession.add_message(session_id, "user", message, user_message_metadata)
        
        # Initialize lead tracking variables
        original_lead_id = lead_id
        lead_created = False
        lead_updated = False
        extracted_lead_id = None
        
        # ✅ FIX D: Add debug logging for Enhanced RAG processing
        logging.info(f"DEBUG: Starting RAG processing - Original lead_id: {original_lead_id}, Message: '{message[:50]}...'")
        
        if ENHANCED_RAG_AVAILABLE and enhanced_rag_service:
            # Use enhanced RAG service with conversational memory
            logging.info(f"DEBUG: Calling Enhanced RAG for session {session_id}")
            
            result = enhanced_rag_service.query(
                question=message,
                university_code=university_code,
                university_x_id=university_x_id,
                session_id=session_id,
                lead_id=lead_id
            )
            
            # ✅ FIX D: Debug log Enhanced RAG result
            logging.info(f"DEBUG: Enhanced RAG completed - Error: {result.get('error')}, Lead ID in result: {result.get('lead_id')}")
            
            if result.get('error'):
                # Fallback to simple RAG
                logging.warning(f"Enhanced RAG failed, falling back to simple RAG: {result.get('error')}")
                fallback_result = simple_rag_service.query(
                    question=message,
                    university_code=university_code,
                    session_id=session_id
                )
                response = fallback_result.get('answer', "I'm sorry, but I don't have information about that topic.")
                metadata = {
                    "error": True,
                    "fallback_used": True,
                    "rag_approach": "enhanced_with_simple_fallback",
                    "error_message": result.get('error', 'Unknown error'),
                    "is_public_session": is_public,
                    "enhanced_rag_attempted": True,
                    "lead_id": lead_id,
                    "lead_created": False,
                    "lead_updated": False
                }
                
                # ✅ FIX D: Debug log fallback
                logging.info(f"DEBUG: Using fallback RAG due to Enhanced RAG error")
                
            else:
                response = result.get('answer', 'I apologize, but I could not generate a response.')
                
                # Extract lead information from Enhanced RAG result
                extracted_lead_id = result.get('lead_id')
                
                # ✅ FIX D: Debug log lead extraction result
                logging.info(f"DEBUG: Enhanced RAG returned lead_id: {extracted_lead_id}")
                
                # Check if a new lead was created during processing
                if extracted_lead_id and extracted_lead_id != original_lead_id:
                    if not original_lead_id:
                        lead_created = True
                        lead_id = extracted_lead_id
                        # ✅ FIXED: Remove emoji from log
                        logging.info(f"SUCCESS: NEW LEAD CREATED: {extracted_lead_id} from message: '{message[:50]}...'")
                    else:
                        lead_updated = True
                        lead_id = extracted_lead_id
                        # ✅ FIXED: Remove emoji from log
                        logging.info(f"SUCCESS: LEAD UPDATED: {extracted_lead_id} from message: '{message[:50]}...'")
                elif extracted_lead_id == original_lead_id:
                    # ✅ FIX D: Debug log when lead ID matches
                    logging.info(f"DEBUG: Lead ID confirmed (no change): {extracted_lead_id}")
                else:
                    # ✅ FIX D: Debug log when no lead extracted
                    logging.warning(f"DEBUG: NO LEAD extracted from Enhanced RAG for message: '{message[:50]}...'")
                
                metadata = {
                    "rag_approach": "enhanced_conversational",
                    "conversation_aware": result.get('conversation_context', {}),
                    "contains_question": result.get('contains_question', False),
                    "sources": result.get('source_documents', [])[:3],
                    "is_public_session": is_public,
                    "lead_id": lead_id,  # Return updated lead_id
                    "lead_created": lead_created,  # Track lead creation
                    "lead_updated": lead_updated,  # Track lead updates
                    "extracted_lead_id": extracted_lead_id,  # Track extraction result
                    "processing_time": result.get('processing_time', 0),
                    "from_cache": result.get('from_cache', False),
                    "enhanced_rag_used": True
                }
                
                # Add enhanced features metadata
                if result.get('conversation_context'):
                    metadata.update({
                        "user_name": result.get('user_name'),
                        "question_type": result.get('question_type'),
                        "conversation_turn": len(result.get('conversation_context', {}).get('message_history', []))
                    })
                
                # ✅ FIX D: Debug log metadata creation
                logging.info(f"DEBUG: Metadata created - Lead created: {lead_created}, Lead updated: {lead_updated}, Final lead_id: {lead_id}")
                
        else:
            # Use simple RAG service only
            logging.info(f"DEBUG: Using Simple RAG (Enhanced RAG not available)")
            
            result = simple_rag_service.query(
                question=message,
                university_code=university_code,
                session_id=session_id
            )
            
            response = result.get('answer', "I'm sorry, but I don't have information about that topic.")
            metadata = {
                "rag_approach": "simple_only",
                "sources": result.get('source_documents', [])[:3],
                "is_public_session": is_public,
                "lead_id": lead_id,
                "lead_created": False,
                "lead_updated": False,
                "enhanced_rag_used": False,
                "processing_time": result.get('processing_time', 0)
            }
        
        # Store assistant response with complete lead information
        assistant_metadata = {
            **metadata,
            "lead_id": lead_id,  # Ensure lead_id is included
            "timestamp": datetime.utcnow()
        }
        
        ChatSession.add_message(session_id, "assistant", response, assistant_metadata)
        
        # ✅ FIX D: Debug log assistant message storage
        logging.info(f"DEBUG: Stored assistant message with lead_id: {lead_id}")
        
        # Store in lead's live chat summaries if we have a lead_id
        if lead_id and is_public:  # Only for public sessions (authenticated sessions handle this elsewhere)
            try:
                Lead.add_live_chat_summary(
                    lead_id=lead_id,
                    session_id=session_id,
                    user_message=message,
                    assistant_response=response,
                    metadata=assistant_metadata
                )
                # ✅ FIXED: Remove emoji from log
                logging.info(f"SUCCESS: Stored chat summary for lead: {lead_id}")
            except Exception as summary_error:
                logging.warning(f"Failed to store chat summary: {summary_error}")
        else:
            # ✅ FIX D: Debug log when chat summary not stored
            if not lead_id:
                logging.info(f"DEBUG: No chat summary stored - no lead_id")
            elif not is_public:
                logging.info(f"DEBUG: No chat summary stored - not a public session")
        
        # ✅ FIX D: Debug log final result
        logging.info(f"DEBUG: RAG processing complete - Final lead_id: {lead_id}, Lead created: {lead_created}, Lead updated: {lead_updated}")
        
        # Return complete metadata including lead information
        final_metadata = {
            **metadata,
            "session_id": session_id,
            "university_x_id": university_x_id,
            "message_stored": True,
            "chat_summary_stored": bool(lead_id and is_public)
        }
        
        return response, final_metadata
        
    except Exception as e:
        logging.error(f"Error in RAG query processing: {str(e)}")
        # ✅ FIX D: Debug log the full exception
        import traceback
        logging.error(f"DEBUG: Full exception traceback: {traceback.format_exc()}")
        
        error_response = f"I apologize, but I encountered an error while processing your question. Please try rephrasing or ask about our programs, admissions, or facilities."
        error_metadata = {
            "error": True,
            "rag_approach": "error_fallback",
            "error_message": str(e),
            "is_public_session": is_public,
            "enhanced_rag_used": ENHANCED_RAG_AVAILABLE,
            "lead_id": lead_id,
            "lead_created": False,
            "lead_updated": False,
            "session_id": session_id,
            "university_x_id": university_x_id
        }
        return error_response, error_metadata
    
