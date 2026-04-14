from flask import Blueprint, request, jsonify
from app.models.lead import Lead
from app.models import leads_collection, chat_sessions_collection
from app.models.chat import ChatSession
from app.models.university import University
from app.services.simple_rag_service import SimpleRAGService
from datetime import datetime
import logging
from functools import wraps
import jwt
import os
from app.models import users_collection
from bson import ObjectId
from app.utils import require_admin_or_above

# Enhanced RAG service integration with fallback
try:
    from app.services.enhanced_rag import EnhancedRAGService
    ENHANCED_RAG_AVAILABLE = True
except ImportError:
    ENHANCED_RAG_AVAILABLE = False

JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')

lead_bp = Blueprint('lead', __name__)

# Initialize RAG service with enhanced capabilities when available
if ENHANCED_RAG_AVAILABLE:
    try:
        enhanced_rag_service = EnhancedRAGService()
        rag_service = enhanced_rag_service
        logging.info("Lead routes using Enhanced RAG Service with conversational memory")
    except Exception as e:
        rag_service = SimpleRAGService()
        logging.warning(f"Enhanced RAG Service failed to initialize, using Simple RAG: {e}")
else:
    rag_service = SimpleRAGService()
    logging.info("Lead routes using Simple RAG Service (enhanced service not available)")

def require_auth(f):
    """Decorator to require authentication for endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({"error": "Authentication token required"}), 401
            
            if token.startswith('Bearer '):
                token = token[7:]
            
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            user_id = payload['user_id']
            
            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user or not user.get('is_active', True):
                return jsonify({"error": "Invalid or inactive user"}), 401
            
            # Add user info to request context
            request.current_user = {
                'id': user_id,
                'email': user['email'], 
                'role': user['role']
            }
            
            # ✅ CRITICAL: Add university context for admin users
            if user['role'] == 'admin':
                request.current_user['university_x_id'] = user.get('university_x_id')
                request.current_user['university_code'] = user.get('university_code')
            
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid authentication token"}), 401
        except Exception as e:
            return jsonify({"error": f"Authentication failed: {str(e)}"}), 500
    
    return decorated_function

@lead_bp.route('/create', methods=['POST'])
def create_lead():
    """
    Create a new lead or return existing lead with chat summaries
    Enhanced with X-ID support and university validation
    """
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        country = data.get('country')
        mobile = data.get('mobile')  # Optional field
        
        # Enhanced university identification - support both X-ID and code
        university_x_id = data.get('university_x_id')
        university_code = data.get('university_code')
        
        # SOLUTION C: Remove hardcoded university - must provide either X-ID or code
        if not university_x_id and not university_code:
            return jsonify({"error": "Either university_x_id or university_code is required"}), 400
        
        if not name or not email or not country:
            return jsonify({"error": "Name, email, and country are required"}), 400
        
        # Enhanced email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({"error": "Invalid email format"}), 400
        
        # University validation and X-ID resolution
        university = None
        if university_x_id:
            university = University.get_university_by_x_id(university_x_id)
            if not university:
                return jsonify({"error": f"University with X-ID '{university_x_id}' not found"}), 404
            university_code = university['code']
        else:
            # Try to get university by code for validation
            university = University.get_university_by_code(university_code)
            if not university:
                return jsonify({"error": f"University with code '{university_code}' not found"}), 404
            university_x_id = university.get('x_id')
        
        # Create lead with validated university code
        lead_id, is_existing = Lead.create_lead(name, email, university_code, country, mobile)
        
        response_data = {
            "success": True,
            "lead_id": lead_id,
            "is_existing_lead": is_existing,
            "university_code": university_code,
            "university_x_id": university_x_id
        }
        
        # Add university information
        if university:
            response_data.update({
                "university_name": university.get('name'),
                "university_branding": university.get('branding', {})
            })
        
        if is_existing:
            # Get complete chat history for existing lead
            complete_history = Lead.get_complete_chat_history(lead_id)
            response_data.update({
                "message": f"Welcome back! We found your previous interactions with {university.get('name', university_code)}.",
                "complete_chat_history": complete_history,
                "returning_lead": True
            })
        else:
            response_data.update({
                "message": f"Welcome! Your profile has been created for {university.get('name', university_code)}.",
                "returning_lead": False
            })
        
        return jsonify(response_data)
        
    except Exception as e:
        logging.error(f"Error creating lead: {str(e)}")
        return jsonify({"error": "Failed to create lead", "details": str(e)}), 500

@lead_bp.route('/get-complete-history/<lead_id>', methods=['GET'])
def get_complete_chat_history(lead_id):
    """SOLUTION A: Get complete chat history for a specific lead"""
    try:
        session_id = request.args.get('session_id')  # Optional filter by session
        
        complete_history = Lead.get_complete_chat_history(lead_id, session_id)
        if complete_history is None:
            return jsonify({"error": "Lead not found"}), 404
        
        return jsonify({
            "success": True,
            "complete_history": complete_history
        })
        
    except Exception as e:
        logging.error(f"Error getting complete chat history: {str(e)}")
        return jsonify({"error": "Failed to get complete chat history"}), 500

@lead_bp.route('/start-agentic-chat', methods=['POST'])
def start_agentic_chat():
    """
    Start agentic chat session for a lead with enhanced university-specific customization
    SOLUTION A & C: Complete message storage and X-ID dependency
    """
    try:
        data = request.get_json()
        lead_id = data.get('lead_id')
        university_x_id = data.get('university_x_id')
        university_code = data.get('university_code')
        
        if not lead_id:
            return jsonify({"error": "Lead ID is required"}), 400
        
        # SOLUTION C: Must provide university identifier
        if not university_x_id and not university_code:
            return jsonify({"error": "Either university_x_id or university_code is required"}), 400
        
        # Get lead information
        lead = Lead.get_lead_by_id(lead_id)
        if not lead:
            return jsonify({"error": "Lead not found"}), 404
        
        # Enhanced university resolution
        university = None
        if university_x_id:
            university = University.get_university_by_x_id(university_x_id)
            if not university:
                return jsonify({"error": f"University with X-ID '{university_x_id}' not found"}), 404
            university_code = university['code']
        else:
            university = University.get_university_by_code(university_code)
            if not university:
                return jsonify({"error": f"University with code '{university_code}' not found"}), 404
            university_x_id = university.get('x_id')
        
        # Create chat session using appropriate method
        if university_x_id:
            session_id = ChatSession.create_session_by_x_id(university_x_id, lead_id)
        else:
            session_id = ChatSession.create_session(university_code, lead_id)
        
        # Add session to lead
        Lead.add_chat_session(lead_id, session_id)
        
        # Create personalized welcome message based on university
        lead_name = lead.get('name', 'there')
        university_name = university.get('name', university_code.upper())
        
        # Get university branding for personalized messaging
        branding = university.get('branding', {})
        custom_greeting = branding.get('custom_greeting', '')
        
        if custom_greeting:
            welcome_message = custom_greeting.format(
                name=lead_name, 
                university=university_name
            )
        else:
            # SOLUTION C: Dynamic welcome message based on university
            welcome_message = (
                f"Hello {lead_name}! Welcome to {university_name}! 🎓\n\n"
                f"I'm your AI assistant, and I'm here to help you discover everything about our programs, "
                f"admissions process, facilities, and answer any questions you might have.\n\n"
                f"Whether you're interested in undergraduate programs, postgraduate studies, scholarships, "
                f"or campus life, I'm here to guide you every step of the way.\n\n"
                f"How can I assist you today?"
            )
        
        # SOLUTION A: Add welcome message to session WITH complete storage
        ChatSession.add_message(session_id, "assistant", welcome_message, {
            "message_type": "welcome",
            "personalized": True,
            "university_x_id": university_x_id,
            "lead_name": lead_name,
            "lead_id": lead_id  # This ensures it gets stored in lead's complete history
        })
        
        # Prepare response with enhanced information
        response_data = {
            "success": True,
            "session_id": session_id,
            "lead_id": lead_id,
            "lead_name": lead_name,
            "welcome_message": welcome_message,
            "university_code": university_code,
            "university_x_id": university_x_id,
            "university_name": university_name,
            "enhanced_rag_available": ENHANCED_RAG_AVAILABLE,
            "complete_storage_enabled": True  # NEW: Indicates all messages are stored
        }
        
        # Add university-specific information
        response_data.update({
            "university_branding": branding,
            "personalized_experience": True
        })
        
        return jsonify(response_data)
        
    except Exception as e:
        logging.error(f"Error starting agentic chat: {str(e)}")
        return jsonify({"error": "Failed to start chat session", "details": str(e)}), 500

@lead_bp.route('/chat', methods=['POST'])
def agentic_chat():
    """
    Handle agentic chat messages with enhanced RAG and COMPLETE message storage
    SOLUTION A: Every message stored in both session and lead complete history
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        message = data.get('message')
        lead_id = data.get('lead_id')
        
        if not session_id or not message:
            return jsonify({"error": "Session ID and message are required"}), 400
        
        # Get session
        session = ChatSession.get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        university_code = session.get('university_code')
        university_x_id = session.get('university_x_id')
        
        # SOLUTION A: Store user message with complete metadata
        ChatSession.add_message(session_id, "user", message, {
            "lead_id": lead_id,
            "processing_method": "enhanced_rag" if ENHANCED_RAG_AVAILABLE else "simple_rag",
            "university_x_id": university_x_id,
            "timestamp": datetime.utcnow()
        })

        original_lead_id = lead_id  # ✅ FIXED: Track original lead_id
        extracted_lead_id = None
        lead_created = False
        lead_updated = False
        
        # Enhanced RAG query with lead context
        if ENHANCED_RAG_AVAILABLE:
            result = rag_service.query(
                question=message,
                university_code=university_code,
                university_x_id=university_x_id,
                session_id=session_id,
                lead_id=lead_id,
                is_first_message=session.get('message_count', 0) <= 1
            )
        else:
            result = rag_service.query(
                question=message,
                university_code=university_code,
                session_id=session_id
            )
        
        # ✅ FIXED: Process Enhanced RAG results for lead extraction
        if ENHANCED_RAG_AVAILABLE and not result.get('error'):
            # Extract lead_id from Enhanced RAG result
            extracted_lead_id = result.get('lead_id')
            
            # Check if a new lead was created or existing lead updated
            if extracted_lead_id:
                if not original_lead_id:
                    # New lead created
                    lead_id = extracted_lead_id
                    lead_created = True
                    logging.info(f"✅ NEW LEAD CREATED by Enhanced RAG: {extracted_lead_id} from message: '{message[:50]}...'")
                elif extracted_lead_id != original_lead_id:
                    # Lead updated or different lead found
                    lead_id = extracted_lead_id
                    lead_updated = True
                    logging.info(f"✅ LEAD UPDATED by Enhanced RAG: {extracted_lead_id} (was {original_lead_id})")
                else:
                    # Same lead, might have been updated with new info
                    lead_id = extracted_lead_id
                    logging.debug(f"Lead {extracted_lead_id} confirmed by Enhanced RAG")
        
        # Process result with enhanced error handling
        if result.get('error'):
            # Get university name for better error messages (SOLUTION C: Dynamic)
            university = University.get_university_by_x_id(university_x_id) if university_x_id else None
            university_name = university.get('name', 'our university') if university else 'our university'
            
            response = (
                f"I'm sorry, but I don't have specific information about that topic for {university_name}. "
                f"However, I'm here to help with questions about our programs, admissions process, "
                f"facilities, fees, scholarships, and campus life. What would you like to know more about?"
            )
            metadata = {
                "error": True,
                "fallback_response": True,
                "university_name": university_name,
                "university_x_id": university_x_id,
                "enhanced_rag_used": ENHANCED_RAG_AVAILABLE,
                "lead_id": lead_id,  # ✅ FIXED: Include current lead_id
                "lead_created": lead_created,
                "lead_updated": lead_updated
            }
        else:
            response = result.get('answer', 'I apologize, but I could not generate a response.')
            metadata = {
                "sources": result.get('source_documents', [])[:3],
                "rag_success": True,
                "enhanced_rag_used": ENHANCED_RAG_AVAILABLE,
                "processing_time": result.get('processing_time', 0),
                "from_cache": result.get('from_cache', False),
                "university_x_id": university_x_id,
                "lead_id": lead_id,  # ✅ FIXED: Use updated lead_id
                "lead_created": lead_created,
                "lead_updated": lead_updated,
                "extracted_lead_id": extracted_lead_id,
                "original_lead_id": original_lead_id
            }
            
            # Add enhanced RAG specific metadata if available
            if ENHANCED_RAG_AVAILABLE:
                metadata.update({
                    "conversation_context": result.get('conversation_context', {}),
                    "contains_question": result.get('contains_question', False),
                    "question_type": result.get('question_type'),
                    "user_name": result.get('user_name')
                })
        
        # ✅ FIXED: Store assistant response in chat session WITH updated lead_id
        ChatSession.add_message(session_id, "assistant", response, {
            **metadata,
            "lead_id": lead_id,  # Use updated lead_id
            "timestamp": datetime.utcnow()
        })
        
        # ✅ FIXED: Store in lead's live chat summaries if we have a lead_id
        if lead_id:
            Lead.add_live_chat_summary(
                lead_id=lead_id,
                session_id=session_id,
                user_message=message,
                assistant_response=response,
                metadata=metadata
            )
            logging.info(f"✅ Stored live chat summary for lead: {lead_id}")
        
        # ✅ FIXED: Prepare enhanced response with complete lead information
        response_data = {
            "success": True,
            "response": response,
            "session_id": session_id,
            "university_x_id": university_x_id,
            "chat_stored_completely": True,
            "enhanced_rag_used": ENHANCED_RAG_AVAILABLE,
            "lead_id": lead_id,  # ✅ FIXED: Return updated lead_id to frontend
            "lead_created": lead_created,  # ✅ FIXED: Inform frontend about lead creation
            "lead_updated": lead_updated,  # ✅ FIXED: Inform frontend about lead updates
            "processing_metadata": {
                "processing_time": metadata.get('processing_time', 0),
                "from_cache": metadata.get('from_cache', False),
                "sources_count": len(metadata.get('sources', []))
            }
        }
        
        # ✅ FIXED: Add enhanced features info if available
        if ENHANCED_RAG_AVAILABLE and result.get('conversation_context'):
            response_data["conversation_features"] = {
                "user_name_detected": bool(result.get('user_name')),
                "contains_follow_up_question": result.get('contains_question', False),
                "conversation_turn": len(result.get('conversation_context', {}).get('message_history', [])),
                "lead_extraction_performed": extracted_lead_id is not None,
                "dynamic_questioning_active": bool(result.get('dynamic_question'))
            }
        
        return jsonify(response_data)
        
    except Exception as e:
        logging.error(f"Error in agentic chat: {str(e)}")
        return jsonify({
            "error": "Failed to process chat message", 
            "details": str(e),
            "session_id": session_id
        }), 500

# SOLUTION B: Enhanced admin routes filtered by X-ID
@lead_bp.route('/get-leads', methods=['GET'])
@require_auth
def get_leads():
    """Get leads based on user role and university X-ID assignment"""
    try:
        user_role = request.current_user.get('role')
        
        if user_role == 'superadmin':
            # SuperAdmin sees all leads with complete history
            leads = Lead.get_leads_with_complete_history(limit=100)
            
        elif user_role == 'admin':
            # SOLUTION B: Admin sees only their university leads by X-ID
            university_x_id = request.current_user.get('university_x_id')
            
            if not university_x_id:
                return jsonify({"error": "Admin not assigned to university X-ID"}), 403
            
            # Get leads filtered by X-ID with complete history
            leads = Lead.get_leads_with_complete_history(university_x_id, limit=100)
            
        else:
            return jsonify({"error": "Insufficient permissions"}), 403
            
        # Convert ObjectId to string
        for lead in leads:
            lead['_id'] = str(lead['_id'])
            
            if 'live_chat_summaries' in lead:
                for chat in lead['live_chat_summaries']:
                    if 'timestamp' in chat and hasattr(chat['timestamp'], 'isoformat'):
                        chat['timestamp'] = chat['timestamp'].isoformat()

        return jsonify({
            "success": True,
            "leads": leads,
            "total_count": len(leads),
            "filtered_by_x_id": user_role == 'admin',
            "university_x_id": request.current_user.get('university_x_id') if user_role == 'admin' else None
        })
        
    except Exception as e:
        logging.error(f"Error in get_leads: {str(e)}")
        return jsonify({"error": f"Failed to get leads: {str(e)}"}), 500
    
# Add these NEW ROUTES to your existing routes/lead_routes.py file

@lead_bp.route('/leads/<lead_id>/categorize', methods=['PUT'])
@require_auth
def update_lead_categorization(lead_id):
    """Update lead categorization (Hot/Cold/Not Defined)"""
    try:
        data = request.get_json()
        lead_type = data.get('lead_type')
        notes = data.get('notes', '')
        
        if not lead_type:
            return jsonify({
                "success": False,
                "error": "lead_type is required"
            }), 400
        
        if lead_type not in Lead.LEAD_TYPES:
            return jsonify({
                "success": False,
                "error": f"Invalid lead_type. Must be one of: {list(Lead.LEAD_TYPES.keys())}"
            }), 400
        
        # Check if lead exists by trying to get it
        existing_leads = Lead.get_all_leads(1)  # Get 1 lead to check if method works
        
        # We'll let the update method handle the existence check
        # since it returns False if lead doesn't exist
        
        # Update categorization
        success = Lead.update_lead_categorization(lead_id, lead_type, notes)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Lead categorized as {Lead.LEAD_TYPES[lead_type]}",
                "lead_id": lead_id,
                "lead_type": lead_type
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to update lead categorization"
            }), 500
            
    except Exception as e:
        logging.error(f"Error updating lead categorization: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@lead_bp.route('/dashboard/categorization-stats', methods=['GET'])
@require_auth
def get_categorization_stats():
    """Get lead categorization statistics for dashboard"""
    try:
        user_role = request.current_user.get('role')
        
        if user_role == 'admin':
            # Admin sees only their university stats
            university_x_id = request.current_user.get('university_x_id')
            if not university_x_id:
                return jsonify({
                    "success": False,
                    "error": "Admin not assigned to university"
                }), 400
                
            stats = Lead.get_categorization_stats(university_x_id)
        elif user_role == 'superadmin':
            # SuperAdmin sees global stats
            stats = Lead.get_categorization_stats()
        else:
            return jsonify({
                "success": False,
                "error": "Unauthorized"
            }), 403
        
        return jsonify({
            "success": True,
            "categorization_stats": stats,
            "breakdown": {
                "hot_percentage": round((stats['hot'] / max(stats['total'], 1)) * 100, 1),
                "cold_percentage": round((stats['cold'] / max(stats['total'], 1)) * 100, 1),
                "not_defined_percentage": round((stats['not_defined'] / max(stats['total'], 1)) * 100, 1)
            }
        })
        
    except Exception as e:
        logging.error(f"Error getting categorization stats: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to get categorization statistics"
        }), 500

@lead_bp.route('/leads/by-category', methods=['GET'])
@require_auth
def get_leads_by_category():
    """Get leads filtered by category"""
    try:
        user_role = request.current_user.get('role')
        category = request.args.get('category', 'all')
        limit = int(request.args.get('limit', 50))
        
        if user_role == 'admin':
            university_x_id = request.current_user.get('university_x_id')
            if not university_x_id:
                return jsonify({
                    "success": False,
                    "error": "Admin not assigned to university"
                }), 400
        elif user_role == 'superadmin':
            university_x_id = request.args.get('university_x_id')
        else:
            return jsonify({
                "success": False,
                "error": "Unauthorized"
            }), 403
        
        # Get filtered leads
        if category == 'all':
            leads = Lead.get_leads_by_university_x_id(university_x_id, limit)
        else:
            leads = Lead.get_leads_by_category(university_x_id, category, limit)
        
        return jsonify({
            "success": True,
            "leads": leads,
            "filter": {
                "category": category,
                "university_x_id": university_x_id,
                "total_count": len(leads)
            }
        })
        
    except Exception as e:
        logging.error(f"Error getting leads by category: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to get leads by category"
        }), 500

@lead_bp.route('/dashboard/session-trends', methods=['GET'])
@require_auth
def get_session_trends():
    """Get session trends data for dashboard charts"""
    try:
        user_role = request.current_user.get('role')
        
        # Get time range parameters
        time_range = request.args.get('range', 'week')  # week, month, quarter
        
        if user_role == 'admin':
            university_x_id = request.current_user.get('university_x_id')
            if not university_x_id:
                return jsonify({
                    "success": False,
                    "error": "Admin not assigned to university"
                }), 400
                
            trends = get_university_session_trends(university_x_id, time_range)
        elif user_role == 'superadmin':
            university_x_id = request.args.get('university_x_id')
            trends = get_university_session_trends(university_x_id, time_range)
        else:
            return jsonify({
                "success": False,
                "error": "Unauthorized"
            }), 403
        
        return jsonify({
            "success": True,
            "session_trends": trends,
            "time_range": time_range
        })
        
    except Exception as e:
        logging.error(f"Error getting session trends: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to get session trends"
        }), 500
    

@lead_bp.route('/dashboard/enhanced-metrics', methods=['GET'])
@require_auth
def get_enhanced_metrics():
    """Get enhanced dashboard metrics"""
    try:
        user_role = request.current_user.get('role')
        
        if user_role == 'admin':
            university_x_id = request.current_user.get('university_x_id')
            if not university_x_id:
                return jsonify({
                    "success": False,
                    "error": "Admin not assigned to university"
                }), 400
                
            metrics = get_university_enhanced_metrics(university_x_id)
        elif user_role == 'superadmin':
            university_x_id = request.args.get('university_x_id')
            metrics = get_university_enhanced_metrics(university_x_id)
        else:
            return jsonify({
                "success": False,
                "error": "Unauthorized"
            }), 403
        
        return jsonify({
            "success": True,
            "enhanced_metrics": metrics
        })
        
    except Exception as e:
        logging.error(f"Error getting enhanced metrics: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to get enhanced metrics"
        }), 500


@lead_bp.route('/analytics/<university_x_id>', methods=['GET'])
@require_auth
@require_admin_or_above
def get_university_lead_analytics(university_x_id):
    """
    SOLUTION B: Get comprehensive lead analytics for a specific university by X-ID
    Enhanced with complete message history insights
    """
    try:
        # Validate university
        university = University.get_university_by_x_id(university_x_id)
        if not university:
            return jsonify({"error": f"University with X-ID '{university_x_id}' not found"}), 404
        
        # Get comprehensive analytics
        analytics = Lead.get_university_lead_analytics(university_x_id)
        
        # Add session analytics
        session_analytics = ChatSession.get_university_session_analytics(university_x_id)
        
        # Combine analytics
        combined_analytics = {
            **analytics,
            "session_analytics": session_analytics,
            "university_name": university.get('name'),
            "complete_message_tracking": True,  # NEW: Indicates complete storage
            "enhanced_features": {
                "enhanced_rag_available": ENHANCED_RAG_AVAILABLE,
                "personalized_conversations": ENHANCED_RAG_AVAILABLE,
                "complete_message_history": True,
                "x_id_based_filtering": True
            }
        }
        
        return jsonify(combined_analytics)
        
    except Exception as e:
        logging.error(f"Error getting lead analytics: {str(e)}")
        return jsonify({"error": "Failed to get lead analytics", "details": str(e)}), 500

@lead_bp.route('/by-university/<university_x_id>', methods=['GET'])
@require_auth
@require_admin_or_above  
def get_leads_by_university(university_x_id):
    """SOLUTION B: Get all leads for a specific university X-ID with complete history"""
    try:
        # Validate university
        university = University.get_university_by_x_id(university_x_id)
        if not university:
            return jsonify({"error": f"University with X-ID '{university_x_id}' not found"}), 404
        
        # Get leads with complete history
        leads = Lead.get_leads_with_complete_history(university_x_id, limit=200)
        
        # Convert ObjectId to string and enhance with session data
        for lead in leads:
            lead['_id'] = str(lead['_id'])
            
            # Add recent session information
            recent_sessions = ChatSession.get_sessions_by_university_x_id(university_x_id, limit=5)
            lead_sessions = [s for s in recent_sessions if s.get('user_id') == lead['_id']]
            lead['recent_sessions'] = len(lead_sessions)
        
        return jsonify({
            "success": True,
            "university_x_id": university_x_id,
            "university_name": university.get('name'),
            "leads": leads,
            "summary": {
                "total_leads": len(leads),
                "complete_history_available": True,
                "x_id_filtered": True
            }
        })
        
    except Exception as e:
        logging.error(f"Error getting leads by university: {str(e)}")
        return jsonify({"error": "Failed to get leads", "details": str(e)}), 500

# SOLUTION A: New endpoint for complete message analytics
@lead_bp.route('/message-analytics/<university_x_id>', methods=['GET'])
@require_auth
@require_admin_or_above
def get_message_analytics(university_x_id):
    """Get detailed message analytics for university with complete history"""
    try:
        # Get all leads for this university
        leads = Lead.get_leads_by_university_x_id(university_x_id, limit=1000)
        
        total_messages = 0
        user_messages = 0
        assistant_messages = 0
        topics_analysis = {}
        
        for lead in leads:
            complete_history = lead.get('complete_chat_history', [])
            total_messages += len(complete_history)
            
            for msg in complete_history:
                if msg.get('message_type') == 'user':
                    user_messages += 1
                elif msg.get('message_type') == 'assistant':
                    assistant_messages += 1
                
                # Analyze topics from metadata
                if msg.get('metadata', {}).get('topics'):
                    for topic in msg['metadata']['topics']:
                        topics_analysis[topic] = topics_analysis.get(topic, 0) + 1
        
        return jsonify({
            "university_x_id": university_x_id,
            "message_analytics": {
                "total_messages": total_messages,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "average_messages_per_lead": round(total_messages / len(leads), 2) if leads else 0
            },
            "topics_analysis": topics_analysis,
            "leads_analyzed": len(leads),
            "complete_history_analyzed": True
        })
        
    except Exception as e:
        logging.error(f"Error getting message analytics: {str(e)}")
        return jsonify({"error": "Failed to get message analytics", "details": str(e)}), 500
    

def get_university_session_trends(university_x_id, time_range='week'):
    """Get session trends for a university"""
    try:
        from datetime import datetime, timedelta
        from app.models import chat_sessions_collection
        
        # Calculate date range
        now = datetime.utcnow()
        if time_range == 'week':
            start_date = now - timedelta(days=7)
            date_format = "%Y-%m-%d"
        elif time_range == 'month':
            start_date = now - timedelta(days=30)
            date_format = "%Y-%m-%d"
        else:  # quarter
            start_date = now - timedelta(days=90)
            date_format = "%Y-%m"
        
        # Build aggregation pipeline
        pipeline = [
            {
                "$match": {
                    "university_x_id": university_x_id,
                    "created_at": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": date_format,
                            "date": "$created_at"
                        }
                    },
                    "session_count": {"$sum": 1},
                    "total_messages": {"$sum": "$message_count"},
                    "avg_duration": {"$avg": "$duration_minutes"}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        results = list(chat_sessions_collection.aggregate(pipeline))
        
        # Format results
        trends = {
            "dates": [result["_id"] for result in results],
            "session_counts": [result["session_count"] for result in results],
            "message_counts": [result["total_messages"] for result in results],
            "avg_durations": [result.get("avg_duration", 0) for result in results]
        }
        
        return trends
        
    except Exception as e:
        logging.error(f"Error getting session trends: {str(e)}")
        return {
            "dates": [],
            "session_counts": [],
            "message_counts": [],
            "avg_durations": []
        }

def get_university_enhanced_metrics(university_x_id):
    """Get enhanced metrics for a university"""
    try:
        from datetime import datetime, timedelta
        from app.models import chat_sessions_collection, leads_collection
        
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Session metrics
        total_sessions = chat_sessions_collection.count_documents({
            "university_x_id": university_x_id
        })
        
        weekly_sessions = chat_sessions_collection.count_documents({
            "university_x_id": university_x_id,
            "created_at": {"$gte": week_ago}
        })
        
        # Average session duration
        duration_pipeline = [
            {"$match": {"university_x_id": university_x_id}},
            {"$group": {
                "_id": None,
                "avg_duration": {"$avg": "$duration_minutes"},
                "avg_messages": {"$avg": "$message_count"}
            }}
        ]
        
        duration_result = list(chat_sessions_collection.aggregate(duration_pipeline))
        avg_duration = duration_result[0]["avg_duration"] if duration_result else 0
        avg_messages = duration_result[0]["avg_messages"] if duration_result else 0
        
        # Lead engagement metrics
        engaged_leads = leads_collection.count_documents({
            "university_x_id": university_x_id,
            "live_chat_summaries.1": {"$exists": True}  # Leads with 2+ sessions
        })
        
        total_leads = leads_collection.count_documents({
            "university_x_id": university_x_id
        })
        
        engagement_rate = (engaged_leads / max(total_leads, 1)) * 100
        
        # Top active hours
        active_hours_pipeline = [
            {"$match": {"university_x_id": university_x_id}},
            {"$group": {
                "_id": {"$hour": "$created_at"},
                "session_count": {"$sum": 1}
            }},
            {"$sort": {"session_count": -1}},
            {"$limit": 3}
        ]
        
        active_hours = list(chat_sessions_collection.aggregate(active_hours_pipeline))
        
        return {
            "total_sessions": total_sessions,
            "weekly_sessions": weekly_sessions,
            "avg_session_duration": round(avg_duration, 1) if avg_duration else 0,
            "avg_messages_per_session": round(avg_messages, 1) if avg_messages else 0,
            "engagement_rate": round(engagement_rate, 1),
            "engaged_leads": engaged_leads,
            "total_leads": total_leads,
            "peak_hours": [f"{hour['_id']:02d}:00" for hour in active_hours[:3]],
            "growth_rate": calculate_growth_rate(weekly_sessions, university_x_id)
        }
        
    except Exception as e:
        logging.error(f"Error getting enhanced metrics: {str(e)}")
        return {
            "total_sessions": 0,
            "weekly_sessions": 0,
            "avg_session_duration": 0,
            "avg_messages_per_session": 0,
            "engagement_rate": 0,
            "engaged_leads": 0,
            "total_leads": 0,
            "peak_hours": [],
            "growth_rate": 0
        }

def calculate_growth_rate(current_week_sessions, university_x_id):
    """Calculate week-over-week growth rate"""
    try:
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        two_weeks_ago = now - timedelta(days=14)
        week_ago = now - timedelta(days=7)
        
        previous_week_sessions = chat_sessions_collection.count_documents({
            "university_x_id": university_x_id,
            "created_at": {
                "$gte": two_weeks_ago,
                "$lt": week_ago
            }
        })
        
        if previous_week_sessions == 0:
            return 100 if current_week_sessions > 0 else 0
        
        growth_rate = ((current_week_sessions - previous_week_sessions) / previous_week_sessions) * 100
        return round(growth_rate, 1)
        
    except Exception as e:
        logging.error(f"Error calculating growth rate: {str(e)}")
        return 0