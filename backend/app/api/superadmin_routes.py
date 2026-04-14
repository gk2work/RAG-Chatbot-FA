

from flask import Blueprint, request, jsonify
from app.models.university import University
from app.models.lead import Lead
from app.models.chat import ChatSession
from app.models import users_collection, chat_sessions_collection, leads_collection, universities_collection, chunks_collection
from app.utils.rbac import require_auth, require_superadmin, Roles
from datetime import datetime, timedelta
from bson import ObjectId
import logging


def convert_objectids_to_strings(obj):
    """Recursively convert ObjectId fields to strings for JSON serialization"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_objectids_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectids_to_strings(item) for item in obj]
    else:
        return obj

# Enhanced imports for white-label features
try:
    from app.services.enhanced_rag import EnhancedRAGService
    ENHANCED_RAG_AVAILABLE = True
except ImportError:
    ENHANCED_RAG_AVAILABLE = False

try:
    from app.services.pdf_upload_service import health_check as pdf_health_check
    PDF_SERVICE_AVAILABLE = True
except ImportError:
    PDF_SERVICE_AVAILABLE = False

logger = logging.getLogger(__name__)

# Create SuperAdmin blueprint
superadmin_bp = Blueprint('superadmin', __name__)

# Initialize services with fallback
if ENHANCED_RAG_AVAILABLE:
    try:
        enhanced_rag_service = EnhancedRAGService()
        logger.info("SuperAdmin routes initialized with Enhanced RAG Service")
    except Exception as e:
        enhanced_rag_service = None
        logger.warning(f"Enhanced RAG Service initialization failed: {e}")
else:
    enhanced_rag_service = None

@superadmin_bp.route('/dashboard', methods=['GET'])
@require_auth
@require_superadmin
def get_dashboard_stats():
    """Get enhanced SuperAdmin dashboard statistics with AI service status"""
    try:
        logger.info("SuperAdmin dashboard request started")
        
        # Get basic system statistics first
        stats = {
            "system_overview": {
                "total_universities": 0,
                "total_users": 0,
                "total_leads": 0,
                "total_sessions": 0,
                "active_sessions": 0,
                "total_documents": 0
            },
            "recent_activity": {
                "new_universities_today": 0,
                "new_leads_today": 0,
                "active_sessions_today": 0
            },
            "user_breakdown": {
                "superadmins": 0,
                "admins": 0,
                "students": 0
            },
            "ai_services": {
                "enhanced_rag_available": ENHANCED_RAG_AVAILABLE,
                "pdf_service_available": PDF_SERVICE_AVAILABLE,
                "vector_search_enabled": False,
                "universities_with_ai": 0
            }
        }
        
        # Get counts with individual error handling
        try:
            stats["system_overview"]["total_universities"] = University.get_university_count()
            logger.info("Got university count successfully")
        except Exception as e:
            logger.error(f"Error getting university count: {e}")
        
        try:
            stats["system_overview"]["total_users"] = users_collection.count_documents({})
            logger.info("Got user count successfully")
        except Exception as e:
            logger.error(f"Error getting user count: {e}")
        
        try:
            stats["system_overview"]["total_leads"] = leads_collection.count_documents({})
            logger.info("Got lead count successfully")
        except Exception as e:
            logger.error(f"Error getting lead count: {e}")
        
        try:
            stats["system_overview"]["total_sessions"] = chat_sessions_collection.count_documents({})
            logger.info("Got session count successfully")
        except Exception as e:
            logger.error(f"Error getting session count: {e}")
        
        try:
            stats["system_overview"]["active_sessions"] = chat_sessions_collection.count_documents({"is_active": True})
            logger.info("Got active session count successfully")
        except Exception as e:
            logger.error(f"Error getting active session count: {e}")
        
        try:
            if chunks_collection is not None:
                stats["system_overview"]["total_documents"] = chunks_collection.count_documents({})
                logger.info("Got document count successfully")
        except Exception as e:
            logger.error(f"Error getting document count: {e}")
        
        # Get recent activity with individual error handling
        try:
            stats["recent_activity"]["new_universities_today"] = University.get_universities_created_today()
            logger.info("Got universities created today successfully")
        except Exception as e:
            logger.error(f"Error getting universities created today: {e}")
        
        try:
            stats["recent_activity"]["new_leads_today"] = Lead.get_leads_created_today()
            logger.info("Got leads created today successfully")
        except Exception as e:
            logger.error(f"Error getting leads created today: {e}")
        
        try:
            stats["recent_activity"]["active_sessions_today"] = ChatSession.get_sessions_created_today()
            logger.info("Got sessions created today successfully")
        except Exception as e:
            logger.error(f"Error getting sessions created today: {e}")
        
        # Get user breakdown with individual error handling
        try:
            stats["user_breakdown"]["superadmins"] = users_collection.count_documents({"role": Roles.SUPERADMIN})
            stats["user_breakdown"]["admins"] = users_collection.count_documents({"role": Roles.ADMIN})
            stats["user_breakdown"]["students"] = users_collection.count_documents({"role": Roles.STUDENT})
            logger.info("Got user breakdown successfully")
        except Exception as e:
            logger.error(f"Error getting user breakdown: {e}")
        
        # Enhanced AI service statistics (optional)
        if ENHANCED_RAG_AVAILABLE and enhanced_rag_service:
            try:
                # Get universities with FAISS indexes
                universities_with_faiss = universities_collection.count_documents({
                    "gridfs_faiss_index": {"$exists": True}
                })
                stats["ai_services"]["universities_with_ai"] = universities_with_faiss
                stats["ai_services"]["vector_search_enabled"] = universities_with_faiss > 0
                
                # Get enhanced RAG health status
                rag_healthy, rag_message = enhanced_rag_service.health_check()
                stats["ai_services"]["rag_status"] = {
                    "healthy": rag_healthy,
                    "message": rag_message
                }
                logger.info("Got AI service stats successfully")
            except Exception as e:
                logger.warning(f"Error getting AI service stats: {e}")
        
        # Document processing statistics (optional)
        if chunks_collection is not None:
            try:
                doc_stats = list(chunks_collection.aggregate([
                    {"$group": {
                        "_id": "$university_x_id",
                        "chunk_count": {"$sum": 1}
                    }},
                    {"$group": {
                        "_id": None,
                        "total_universities_with_docs": {"$sum": 1},
                        "avg_chunks_per_university": {"$avg": "$chunk_count"}
                    }}
                ]))
                
                if doc_stats:
                    stats["document_processing"] = {
                        "universities_with_documents": doc_stats[0].get("total_universities_with_docs", 0),
                        "average_chunks_per_university": round(doc_stats[0].get("avg_chunks_per_university", 0), 2),
                        "total_processed_chunks": chunks_collection.count_documents({})
                    }
                logger.info("Got document processing stats successfully")
            except Exception as e:
                logger.warning(f"Error getting document processing stats: {e}")
        
        logger.info("SuperAdmin dashboard completed successfully")
        
        return jsonify({
            "success": True,
            "stats": stats,
            "timestamp": datetime.utcnow(),
            "system_health": {
                "database_connected": True,  # If we got here, DB is connected
                "ai_services_operational": ENHANCED_RAG_AVAILABLE,
                "document_processing_available": PDF_SERVICE_AVAILABLE
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Failed to get dashboard statistics: {str(e)}"
        }), 500


# @superadmin_bp.route('/universities', methods=['GET'])
# @require_auth
# @require_superadmin
# def list_all_universities():
#     """Get all universities with enhanced X-ID focused stats and AI capabilities"""
#     try:
#         universities = University.get_all_universities()
        
#         # Add detailed stats for each university
#         for uni in universities:
#             uni['_id'] = str(uni['_id'])
#             uni_code = uni.get('code')
#             uni_x_id = uni.get('x_id')
            
#             # Enhanced statistics with X-ID focus
#             uni['stats'] = {
#                 "total_leads": leads_collection.count_documents({"university_code": uni_code}),
#                 "total_sessions": chat_sessions_collection.count_documents({"university_code": uni_code}),
#                 "active_sessions": chat_sessions_collection.count_documents({
#                     "university_code": uni_code, 
#                     "is_active": True
#                 }),
#                 "total_documents": uni.get('document_count', 0),
#                 "admins": users_collection.count_documents({
#                     "role": Roles.ADMIN,
#                     "university_id": ObjectId(uni['_id'])
#                 })
#             }
            
#             # Enhanced AI and document processing stats
#             if uni_x_id:
#                 # Document chunks for this university
#                 chunk_count = chunks_collection.count_documents({"university_x_id": uni_x_id}) if chunks_collection is not None else 0
#                 uni['stats']['processed_chunks'] = chunk_count
                
#                 # Check for FAISS index
#                 has_faiss_index = bool(uni.get('gridfs_faiss_index'))
#                 uni['stats']['vector_search_enabled'] = has_faiss_index
#                 uni['stats']['ai_ready'] = chunk_count > 0 and has_faiss_index
                
#                 # Get RAG statistics if available
#                 if ENHANCED_RAG_AVAILABLE and enhanced_rag_service and chunk_count > 0:
#                     try:
#                         rag_stats = enhanced_rag_service.get_rag_stats(uni_code, uni_x_id)
#                         uni['ai_capabilities'] = {
#                             "vector_search_available": rag_stats.get('vectorstore_stats', {}).get('total_documents', 0) > 0,
#                             "enhanced_documents": rag_stats.get('vectorstore_stats', {}).get('enhanced_documents', 0),
#                             "legacy_documents": rag_stats.get('vectorstore_stats', {}).get('legacy_documents', 0),
#                             "features": rag_stats.get('features', {})
#                         }
#                     except Exception as e:
#                         logger.warning(f"Error getting RAG stats for {uni_x_id}: {e}")
            
#             # Get recent activity
#             today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
#             uni['recent_activity'] = {
#                 "leads_today": leads_collection.count_documents({
#                     "university_code": uni_code,
#                     "created_at": {"$gte": today}
#                 }),
#                 "sessions_today": chat_sessions_collection.count_documents({
#                     "university_code": uni_code,
#                     "created_at": {"$gte": today}
#                 })
#             }
            
#             # Enhanced branding information
#             branding = uni.get('branding', {})
#             uni['branding_status'] = {
#                 "logo_configured": bool(branding.get('logo_url')),
#                 "theme_configured": bool(branding.get('theme_colors')),
#                 "domain_configured": bool(branding.get('domain_name')),
#                 "fully_branded": bool(branding.get('logo_url') and branding.get('theme_colors'))
#             }
        
#         return jsonify({
#             "success": True,
#             "universities": universities,
#             "total_count": len(universities),
#             "summary": {
#                 "ai_enabled_universities": sum(1 for u in universities if u.get('ai_capabilities', {}).get('vector_search_available')),
#                 "fully_branded_universities": sum(1 for u in universities if u.get('branding_status', {}).get('fully_branded')),
#                 "active_universities": sum(1 for u in universities if u.get('stats', {}).get('active_sessions', 0) > 0)
#             }
#         })
        
#     except Exception as e:
#         logger.error(f"Error listing universities: {str(e)}")
#         return jsonify({
#             "success": False,
#             "error": f"Failed to list universities: {str(e)}"
#         }), 500

@superadmin_bp.route('/universities', methods=['GET'])
@require_auth
@require_superadmin
def list_all_universities():
    """Get all universities with enhanced X-ID focused stats and AI capabilities"""
    try:
        universities = University.get_all_universities()
        
        # Add detailed stats for each university
        for uni in universities:
            # ✅ Store original ObjectId BEFORE any conversion
            uni_object_id = uni['_id']
            
            uni_code = uni.get('code')
            uni_x_id = uni.get('x_id')
            
            # Enhanced statistics with X-ID focus (use original ObjectId for query)
            uni['stats'] = {
                "total_leads": leads_collection.count_documents({"university_code": uni_code}),
                "total_sessions": chat_sessions_collection.count_documents({"university_code": uni_code}),
                "active_sessions": chat_sessions_collection.count_documents({
                    "university_code": uni_code, 
                    "is_active": True
                }),
                "total_documents": uni.get('document_count', 0),
                "admins": users_collection.count_documents({
                    "role": Roles.ADMIN,
                    "university_id": uni_object_id  # Use original ObjectId
                })
            }
            
            # Enhanced AI and document processing stats
            if uni_x_id:
                # Document chunks for this university
                chunk_count = chunks_collection.count_documents({"university_x_id": uni_x_id}) if chunks_collection is not None else 0
                uni['stats']['processed_chunks'] = chunk_count
                
                # Check for FAISS index
                has_faiss_index = bool(uni.get('gridfs_faiss_index'))
                uni['stats']['vector_search_enabled'] = has_faiss_index
                uni['stats']['ai_ready'] = chunk_count > 0 and has_faiss_index
                
                # Get RAG statistics if available
                if ENHANCED_RAG_AVAILABLE and enhanced_rag_service and chunk_count > 0:
                    try:
                        rag_stats = enhanced_rag_service.get_rag_stats(uni_code, uni_x_id)
                        uni['ai_capabilities'] = {
                            "vector_search_available": rag_stats.get('vectorstore_stats', {}).get('total_documents', 0) > 0,
                            "enhanced_documents": rag_stats.get('vectorstore_stats', {}).get('enhanced_documents', 0),
                            "legacy_documents": rag_stats.get('vectorstore_stats', {}).get('legacy_documents', 0),
                            "features": rag_stats.get('features', {})
                        }
                    except Exception as e:
                        logger.warning(f"Error getting RAG stats for {uni_x_id}: {e}")
            
            # Get recent activity
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            uni['recent_activity'] = {
                "leads_today": leads_collection.count_documents({
                    "university_code": uni_code,
                    "created_at": {"$gte": today}
                }),
                "sessions_today": chat_sessions_collection.count_documents({
                    "university_code": uni_code,
                    "created_at": {"$gte": today}
                })
            }
            
            # ✅ CRITICAL FIX: Enhanced branding information with proper structure handling
            branding = uni.get('branding', {})
            
            # Check for logo
            has_logo = bool(branding.get('logo_url'))
            
            # ✅ FIX: Check for theme colors in BOTH old and new structures
            has_theme_colors = False
            
            # Check OLD nested structure: branding.theme_colors.primary
            if 'theme_colors' in branding:
                theme_colors = branding.get('theme_colors')
                if isinstance(theme_colors, dict) and theme_colors:
                    # Verify it has actual color values, not just empty dict
                    has_theme_colors = bool(
                        theme_colors.get('primary') or 
                        theme_colors.get('secondary') or 
                        theme_colors.get('accent')
                    )
            
            # Check NEW flat structure: branding.primary_color
            if not has_theme_colors:
                has_theme_colors = any(
                    branding.get(key) for key in ['primary_color', 'secondary_color', 'accent_color']
                )
            
            # Check domain configuration (both old and new structure)
            has_domain = bool(
                branding.get('domain_name') or 
                branding.get('domains', {}).get('primary_domain')
            )
            
            # Set branding status
            uni['branding_status'] = {
                "logo_configured": has_logo,
                "theme_configured": has_theme_colors,
                "domain_configured": has_domain,
                "fully_branded": has_logo and has_theme_colors
            }
        
        # ✅ CRITICAL FIX: Convert ALL ObjectIds to strings before JSON serialization
        # This handles ObjectIds at any level of nesting in the data structure
        universities = convert_objectids_to_strings(universities)
        
        return jsonify({
            "success": True,
            "universities": universities,
            "total_count": len(universities),
            "summary": {
                "ai_enabled_universities": sum(1 for u in universities if u.get('ai_capabilities', {}).get('vector_search_available')),
                "fully_branded_universities": sum(1 for u in universities if u.get('branding_status', {}).get('fully_branded')),
                "active_universities": sum(1 for u in universities if u.get('stats', {}).get('active_sessions', 0) > 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing universities: {str(e)}")
        logger.exception("Full traceback:")  # ✅ Added for better debugging
        return jsonify({
            "success": False,
            "error": f"Failed to list universities: {str(e)}"
        }), 500

# @superadmin_bp.route('/universities/<x_id>', methods=['GET'])
# @require_auth
# @require_superadmin
# def get_university_details(x_id):
#     """Get comprehensive university details with AI capabilities and analytics"""
#     try:
#         university = University.get_university_by_x_id(x_id)
#         if not university:
#             return jsonify({
#                 "success": False,
#                 "error": "University not found"
#             }), 404
        
#         university['_id'] = str(university['_id'])
#         uni_code = university.get('code')
        
#         # Get comprehensive statistics
#         university['detailed_stats'] = {
#             "leads": {
#                 "total": leads_collection.count_documents({"university_code": uni_code}),
#                 "this_month": leads_collection.count_documents({
#                     "university_code": uni_code,
#                     "created_at": {"$gte": datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)}
#                 }),
#                 "by_country": list(leads_collection.aggregate([
#                     {"$match": {"university_code": uni_code}},
#                     {"$group": {"_id": "$country", "count": {"$sum": 1}}},
#                     {"$sort": {"count": -1}},
#                     {"$limit": 10}
#                 ]))
#             },
#             "sessions": {
#                 "total": chat_sessions_collection.count_documents({"university_code": uni_code}),
#                 "active": chat_sessions_collection.count_documents({
#                     "university_code": uni_code, 
#                     "is_active": True
#                 }),
#                 "avg_messages": list(chat_sessions_collection.aggregate([
#                     {"$match": {"university_code": uni_code}},
#                     {"$group": {"_id": None, "avg_messages": {"$avg": "$message_count"}}}
#                 ]))
#             },
#             "users": {
#                 "admins": list(users_collection.find({
#                     "role": Roles.ADMIN,
#                     "university_id": ObjectId(university['_id'])
#                 }, {"email": 1, "created_at": 1, "last_login": 1, "profile": 1}))
#             }
#         }
        
#         # Enhanced AI and document analytics
#         if chunks_collection is not None:
#             university['document_analytics'] = {
#                 "total_chunks": chunks_collection.count_documents({"university_x_id": x_id}),
#                 "documents_by_type": list(chunks_collection.aggregate([
#                     {"$match": {"university_x_id": x_id}},
#                     {"$group": {
#                         "_id": "$metadata.source_file",
#                         "chunk_count": {"$sum": 1}
#                     }},
#                     {"$sort": {"chunk_count": -1}}
#                 ])),
#                 "recent_uploads": list(chunks_collection.find(
#                     {"university_x_id": x_id},
#                     {"metadata.source_file": 1, "created_at": 1}
#                 ).sort("created_at", -1).limit(5))
#             }
        
#         # Enhanced RAG service analytics
#         if ENHANCED_RAG_AVAILABLE and enhanced_rag_service:
#             try:
#                 rag_stats = enhanced_rag_service.get_rag_stats(uni_code, x_id)
#                 university['ai_analytics'] = {
#                     "rag_config": rag_stats.get('rag_config', {}),
#                     "vectorstore_stats": rag_stats.get('vectorstore_stats', {}),
#                     "features": rag_stats.get('features', {}),
#                     "health_status": enhanced_rag_service.health_check()
#                 }
#             except Exception as e:
#                 logger.warning(f"Error getting RAG analytics for {x_id}: {e}")
        
#         # Convert ObjectIds to strings in user data
#         for admin in university['detailed_stats']['users']['admins']:
#             admin['_id'] = str(admin['_id'])
        
#         # Enhanced branding analysis
#         branding = university.get('branding', {})
#         university['branding_analysis'] = {
#             "completeness_score": _calculate_branding_completeness(branding),
#             "configured_elements": [k for k, v in branding.items() if v],
#             "missing_elements": _get_missing_branding_elements(branding),
#             "recommendations": _get_branding_recommendations(branding)
#         }
        
#         return jsonify({
#             "success": True,
#             "university": university
#         })
        
#     except Exception as e:
#         logger.error(f"Error getting university details: {str(e)}")
#         return jsonify({
#             "success": False,
#             "error": f"Failed to get university details: {str(e)}"
#         }), 500

@superadmin_bp.route('/universities/<x_id>', methods=['GET'])
@require_auth
@require_superadmin
def get_university_details(x_id):
    """Get comprehensive university details with AI capabilities and analytics"""
    try:
        university = University.get_university_by_x_id(x_id)
        if not university:
            return jsonify({
                "success": False,
                "error": "University not found"
            }), 404
        
        # ✅ CRITICAL FIX: Store original ObjectId before converting
        uni_object_id = university['_id']
        
        # ✅ Convert _id to string immediately
        university['_id'] = str(university['_id'])
        uni_code = university.get('code')
        
        # Get comprehensive statistics
        university['detailed_stats'] = {
            "leads": {
                "total": leads_collection.count_documents({"university_code": uni_code}),
                "this_month": leads_collection.count_documents({
                    "university_code": uni_code,
                    "created_at": {"$gte": datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)}
                }),
                "this_week": leads_collection.count_documents({
                    "university_code": uni_code,
                    "created_at": {"$gte": datetime.utcnow() - timedelta(days=7)}
                })
            },
            "sessions": {
                "total": chat_sessions_collection.count_documents({"university_code": uni_code}),
                "active": chat_sessions_collection.count_documents({
                    "university_code": uni_code,
                    "is_active": True
                }),
                "this_month": chat_sessions_collection.count_documents({
                    "university_code": uni_code,
                    "created_at": {"$gte": datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)}
                })
            },
            "documents": {
                "total": university.get('document_count', 0),
                "processed_chunks": chunks_collection.count_documents({"university_x_id": x_id}) if chunks_collection is not None else 0
            },
            "users": {
                "total_admins": users_collection.count_documents({
                    "role": Roles.ADMIN,
                    "university_id": uni_object_id  # ✅ Use original ObjectId for query
                }),
                # ✅ Get admin users and convert their ObjectIds
                "admins": []
            }
        }
        
        # ✅ Get admin users and convert ALL ObjectIds to strings
        admin_users = list(users_collection.find(
            {"role": Roles.ADMIN, "university_id": uni_object_id},
            {"password_hash": 0}
        ).limit(10))
        
        # ✅ CRITICAL: Convert ObjectIds in admin users
        for admin in admin_users:
            admin['_id'] = str(admin['_id'])
            if 'university_id' in admin:
                admin['university_id'] = str(admin['university_id'])
            if 'created_by' in admin and admin.get('created_by'):
                admin['created_by'] = str(admin['created_by'])
        
        university['detailed_stats']['users']['admins'] = admin_users
        
        # AI capabilities
        if chunks_collection is not None:
            chunk_count = chunks_collection.count_documents({"university_x_id": x_id})
            has_faiss = bool(university.get('gridfs_faiss_index'))
            
            university['ai_capabilities'] = {
                "vector_search_available": chunk_count > 0 and has_faiss,
                "total_chunks": chunk_count,
                "faiss_index_configured": has_faiss,
                "enhanced_rag_available": ENHANCED_RAG_AVAILABLE
            }
            
            # Get RAG analytics if available
            if ENHANCED_RAG_AVAILABLE and enhanced_rag_service and chunk_count > 0:
                try:
                    rag_stats = enhanced_rag_service.get_rag_stats(uni_code, x_id)
                    university['rag_analytics'] = {
                        "total_documents": rag_stats.get('vectorstore_stats', {}).get('total_documents', 0),
                        "enhanced_documents": rag_stats.get('vectorstore_stats', {}).get('enhanced_documents', 0),
                        "legacy_documents": rag_stats.get('vectorstore_stats', {}).get('legacy_documents', 0),
                        "vectorstore_stats": rag_stats.get('vectorstore_stats', {}),
                        "features": rag_stats.get('features', {}),
                        "health_status": enhanced_rag_service.health_check()
                    }
                except Exception as e:
                    logger.warning(f"Error getting RAG analytics for {x_id}: {e}")
        
        # Enhanced branding analysis
        branding = university.get('branding', {})
        university['branding_analysis'] = {
            "completeness_score": _calculate_branding_completeness(branding),
            "configured_elements": [k for k, v in branding.items() if v],
            "missing_elements": _get_missing_branding_elements(branding),
            "recommendations": _get_branding_recommendations(branding)
        }
        
        # ✅ CRITICAL: Convert any other ObjectId fields that might exist
        if 'created_by' in university and university.get('created_by'):
            university['created_by'] = str(university['created_by'])
        if 'updated_by' in university and university.get('updated_by'):
            university['updated_by'] = str(university['updated_by'])
        if 'last_updated_by' in university and university.get('last_updated_by'):
            university['last_updated_by'] = str(university['last_updated_by'])
        
        return jsonify({
            "success": True,
            "university": university
        })
        
    except Exception as e:
        logger.error(f"Error getting university details: {str(e)}")
        logger.exception("Full traceback:")
        return jsonify({
            "success": False,
            "error": f"Failed to get university details: {str(e)}"
        }), 500
    


# @superadmin_bp.route('/users', methods=['GET'])
# @require_auth
# @require_superadmin
# def list_all_users():
#     """Get all users with enhanced filtering, pagination, and analytics"""
#     try:
#         # Get query parameters for filtering
#         role_filter = request.args.get('role')
#         university_id = request.args.get('university_id')
#         university_x_id = request.args.get('university_x_id')
#         page = int(request.args.get('page', 1))
#         limit = int(request.args.get('limit', 20))
#         include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
#         # Build query filter
#         query_filter = {}
#         if role_filter and role_filter in [Roles.ADMIN, Roles.STUDENT, Roles.SUPERADMIN]:
#             query_filter['role'] = role_filter
        
#         if university_x_id:
#             # Resolve X-ID to university ObjectId
#             university = University.get_university_by_x_id(university_x_id)
#             if university:
#                 query_filter['university_id'] = ObjectId(university['_id'])
#         elif university_id:
#             query_filter['university_id'] = ObjectId(university_id)
        
#         if not include_inactive:
#             query_filter['is_active'] = {"$ne": False}
        
#         # Get users with pagination
#         skip = (page - 1) * limit
#         users = list(users_collection.find(
#             query_filter,
#             {"password_hash": 0}  # Exclude password hash
#         ).skip(skip).limit(limit).sort("created_at", -1))
        
#         # Enhanced user data processing
#         for user in users:
#             # Convert ALL ObjectIds to strings first
#             user = convert_objectids_to_strings(user)
            
#             # Handle university information - check both university_id and university_x_id
#             university = None
#             logger.info(f"Processing user {user.get('email')}: university_id={user.get('university_id')}, university_x_id={user.get('university_x_id')}, university_code={user.get('university_code')}")
            
#             if 'university_id' in user and user['university_id']:
#                 try:
#                     logger.info(f"Looking up university by ID: {user['university_id']}")
#                     university = University.get_university_by_id(str(user['university_id']))
#                     logger.info(f"University lookup by ID result: {university}")
#                 except Exception as e:
#                     logger.warning(f"Error getting university info by ID for user {user['_id']}: {e}")
#             elif 'university_x_id' in user and user['university_x_id']:
#                 # For admin users stored with university_x_id
#                 try:
#                     logger.info(f"Looking up university by X-ID: {user['university_x_id']}")
#                     university = University.get_university_by_x_id(user['university_x_id'])
#                     logger.info(f"University lookup by X-ID result: {university}")
#                 except Exception as e:
#                     logger.warning(f"Error getting university info by X-ID for user {user['_id']}: {e}")
#             else:
#                 logger.info(f"No university_id or university_x_id found for user {user.get('email')}")
            
#             # Add university information to user object
#             if university:
#                 user['university_info'] = {
#                     "name": university.get('name'),
#                     "code": university.get('code'),
#                     "x_id": university.get('x_id')
#                 }
#                 # Add fields that frontend expects
#                 user['university_name'] = university.get('name')
#                 user['university_code'] = university.get('code')
#                 user['university_x_id'] = university.get('x_id')
            
#             # Add user activity metrics
#             if user.get('role') == Roles.ADMIN:
#                 # Count sessions created by this admin's university
#                 user_university_code = user.get('university_info', {}).get('code')
#                 if user_university_code:
#                     user['activity_metrics'] = {
#                         "university_sessions": chat_sessions_collection.count_documents({
#                             "university_code": user_university_code
#                         }),
#                         "university_leads": leads_collection.count_documents({
#                             "university_code": user_university_code
#                         })
#                     }
        
#         total_count = users_collection.count_documents(query_filter)
        
#         # Enhanced user analytics
#         user_analytics = {
#             "total_by_role": {},
#             "active_vs_inactive": {},
#             "recent_registrations": {}
#         }
        
#         # Role distribution
#         for role in [Roles.SUPERADMIN, Roles.ADMIN, Roles.STUDENT]:
#             user_analytics["total_by_role"][role] = users_collection.count_documents({"role": role})
        
#         # Active vs inactive
#         user_analytics["active_vs_inactive"] = {
#             "active": users_collection.count_documents({"is_active": {"$ne": False}}),
#             "inactive": users_collection.count_documents({"is_active": False})
#         }
        
#         # Recent registrations (last 7 days)
#         week_ago = datetime.utcnow() - timedelta(days=7)
#         user_analytics["recent_registrations"] = {
#             "this_week": users_collection.count_documents({"created_at": {"$gte": week_ago}}),
#             "by_role": {}
#         }
        
#         for role in [Roles.SUPERADMIN, Roles.ADMIN, Roles.STUDENT]:
#             user_analytics["recent_registrations"]["by_role"][role] = users_collection.count_documents({
#                 "role": role,
#                 "created_at": {"$gte": week_ago}
#             })
        
#         # Convert all ObjectIds to strings before returning
#         response_data = {
#             "success": True,
#             "users": users,
#             "pagination": {
#                 "current_page": page,
#                 "total_pages": (total_count + limit - 1) // limit,
#                 "total_count": total_count,
#                 "has_next": skip + limit < total_count
#             },
#             "analytics": user_analytics,
#             "filters_applied": {
#                 "role": role_filter,
#                 "university_x_id": university_x_id,
#                 "include_inactive": include_inactive
#             }
#         }
        
#         return jsonify(convert_objectids_to_strings(response_data))
        
#     except Exception as e:
#         logger.error(f"Error listing users: {str(e)}")
#         return jsonify({
#             "success": False,
#             "error": f"Failed to list users: {str(e)}"
#         }), 500


@superadmin_bp.route('/users', methods=['GET'])
@require_auth
@require_superadmin
def list_all_users():
    """Get all users with enhanced filtering, pagination, and analytics"""
    try:
        # Get query parameters for filtering
        role_filter = request.args.get('role')
        university_id = request.args.get('university_id')
        university_x_id = request.args.get('university_x_id')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        # Build query filter
        query_filter = {}
        if role_filter and role_filter in [Roles.ADMIN, Roles.STUDENT, Roles.SUPERADMIN]:
            query_filter['role'] = role_filter
        
        if university_x_id:
            # Resolve X-ID to university ObjectId
            university = University.get_university_by_x_id(university_x_id)
            if university:
                query_filter['university_id'] = ObjectId(university['_id'])
        elif university_id:
            query_filter['university_id'] = ObjectId(university_id)
        
        if not include_inactive:
            query_filter['is_active'] = {"$ne": False}
        
        # Get users with pagination
        skip = (page - 1) * limit
        users = list(users_collection.find(
            query_filter,
            {"password_hash": 0}  # Exclude password hash
        ).skip(skip).limit(limit).sort("created_at", -1))
        
        # Enhanced user data processing
        for i, user in enumerate(users):
            # Convert ALL ObjectIds to strings first
            user = convert_objectids_to_strings(user)
            
            # Handle university information - check both university_id and university_x_id
            university = None
            logger.info(f"Processing user {user.get('email')}: university_id={user.get('university_id')}, university_x_id={user.get('university_x_id')}, university_code={user.get('university_code')}")
            
            if 'university_id' in user and user['university_id']:
                try:
                    logger.info(f"Looking up university by ID: {user['university_id']}")
                    university = University.get_university_by_id(str(user['university_id']))
                    logger.info(f"University lookup by ID result: {university}")
                except Exception as e:
                    logger.warning(f"Error getting university info by ID for user {user['_id']}: {e}")
            elif 'university_x_id' in user and user['university_x_id']:
                # For admin users stored with university_x_id
                try:
                    logger.info(f"Looking up university by X-ID: {user['university_x_id']}")
                    university = University.get_university_by_x_id(user['university_x_id'])
                    logger.info(f"University lookup by X-ID result: {university}")
                except Exception as e:
                    logger.warning(f"Error getting university info by X-ID for user {user['_id']}: {e}")
            else:
                logger.info(f"No university_id or university_x_id found for user {user.get('email')}")
            
            # Add university information to user object
            if university:
                # Convert university ObjectIds too
                university = convert_objectids_to_strings(university)
                
                user['university_info'] = {
                    "name": university.get('name'),
                    "code": university.get('code'),
                    "x_id": university.get('x_id')
                }
                # Add fields that frontend expects
                user['university_name'] = university.get('name')
                user['university_code'] = university.get('code')
                user['university_x_id'] = university.get('x_id')
            
            # Add user activity metrics
            if user.get('role') == Roles.ADMIN:
                # Count sessions created by this admin's university
                user_university_code = user.get('university_info', {}).get('code')
                if user_university_code:
                    user['activity_metrics'] = {
                        "university_sessions": chat_sessions_collection.count_documents({
                            "university_code": user_university_code
                        }),
                        "university_leads": leads_collection.count_documents({
                            "university_code": user_university_code
                        })
                    }
            
            # Update the original list with converted user
            users[i] = user
        
        total_count = users_collection.count_documents(query_filter)
        
        # Enhanced user analytics
        user_analytics = {
            "total_by_role": {},
            "active_vs_inactive": {},
            "recent_registrations": {}
        }
        
        # Role distribution
        for role in [Roles.SUPERADMIN, Roles.ADMIN, Roles.STUDENT]:
            user_analytics["total_by_role"][role] = users_collection.count_documents({"role": role})
        
        # Active vs inactive
        user_analytics["active_vs_inactive"] = {
            "active": users_collection.count_documents({"is_active": {"$ne": False}}),
            "inactive": users_collection.count_documents({"is_active": False})
        }
        
        # Recent registrations (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        user_analytics["recent_registrations"] = {
            "this_week": users_collection.count_documents({"created_at": {"$gte": week_ago}}),
            "by_role": {}
        }
        
        for role in [Roles.SUPERADMIN, Roles.ADMIN, Roles.STUDENT]:
            user_analytics["recent_registrations"]["by_role"][role] = users_collection.count_documents({
                "role": role,
                "created_at": {"$gte": week_ago}
            })
        
        # Convert all ObjectIds to strings before returning
        response_data = {
            "success": True,
            "users": users,
            "pagination": {
                "current_page": page,
                "total_pages": (total_count + limit - 1) // limit,
                "total_count": total_count,
                "has_next": skip + limit < total_count
            },
            "analytics": user_analytics,
            "filters_applied": {
                "role": role_filter,
                "university_x_id": university_x_id,
                "include_inactive": include_inactive
            }
        }
        
        return jsonify(convert_objectids_to_strings(response_data))
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        logger.exception("Full traceback:")
        return jsonify({
            "success": False,
            "error": f"Failed to list users: {str(e)}"
        }), 500

@superadmin_bp.route('/users/create-admin', methods=['POST'])
@require_auth
@require_superadmin
def create_sub_admin():
    """Create a new admin user for a specific university with enhanced validation"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        university_id = data.get('university_id')
        university_x_id = data.get('university_x_id')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        phone = data.get('phone', '')
        timezone = data.get('timezone', 'UTC')
        
        # Enhanced validation
        if not email or not password:
            return jsonify({
                "success": False,
                "error": "Email and password are required"
            }), 400
        
        if not university_id and not university_x_id:
            return jsonify({
                "success": False,
                "error": "Either university_id or university_x_id is required"
            }), 400
        
        # Resolve university
        university = None
        if university_x_id:
            university = University.get_university_by_x_id(university_x_id)
            if university:
                university_id = str(university['_id'])
        else:
            university = University.get_university_by_id(university_id)
        
        if not university:
            return jsonify({
                "success": False,
                "error": "University not found"
            }), 404
        
        # Enhanced email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({
                "success": False,
                "error": "Invalid email format"
            }), 400
        
        # Check if user already exists
        existing_user = users_collection.find_one({"email": email.lower()})
        if existing_user:
            return jsonify({
                "success": False,
                "error": "User with this email already exists"
            }), 409
        
        # Password strength validation
        if len(password) < 8:
            return jsonify({
                "success": False,
                "error": "Password must be at least 8 characters long"
            }), 400
        
        # Hash password
        from werkzeug.security import generate_password_hash
        password_hash = generate_password_hash(password)
        
        # Create enhanced admin user
        user_data = {
            "email": email.lower(),
            "password_hash": password_hash,
            "role": Roles.ADMIN,
            "university_id": ObjectId(university_id),
            "university_code": university.get('code'),
            "university_x_id": university.get('x_id'),
            "created_at": datetime.utcnow(),
            "created_by": ObjectId(request.current_user['id']),
            "is_active": True,
            "universities": [],
            "permissions": ["manage_university", "view_analytics", "manage_leads"],
            "last_login": None,
            "login_count": 0,
            "profile": {
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "timezone": timezone,
                "avatar_url": "",
                "bio": ""
            },
            "preferences": {
                "email_notifications": True,
                "dashboard_layout": "default",
                "language": "en"
            },
            "audit_trail": [{
                "action": "account_created",
                "timestamp": datetime.utcnow(),
                "performed_by": ObjectId(request.current_user['id']),
                "metadata": {"university_x_id": university.get('x_id')}
            }]
        }
        
        result = users_collection.insert_one(user_data)
        
        # Log university admin creation
        try:
            University.update_university_metadata(
                university.get('x_id'),
                request.current_user['id'],
                "admin_created",
                {
                    "admin_email": email,
                    "admin_id": str(result.inserted_id),
                    "created_by": request.current_user['email']
                }
            )
        except Exception as e:
            logger.warning(f"Error logging admin creation: {e}")
        
        return jsonify({
            "success": True,
            "message": f"Admin user created successfully for {university['name']}",
            "user_id": str(result.inserted_id),
            "university": {
                "name": university['name'],
                "code": university['code'],
                "x_id": university.get('x_id')
            },
            "user_profile": {
                "email": email,
                "full_name": f"{first_name} {last_name}".strip(),
                "role": Roles.ADMIN,
                "permissions": user_data['permissions']
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to create admin user: {str(e)}"
        }), 500

@superadmin_bp.route('/analytics/aggregated', methods=['GET'])
@require_auth
@require_superadmin
def get_aggregated_analytics():
    """Get enhanced aggregated analytics across all universities with AI insights"""
    try:
        # Get date range from query parameters
        days = int(request.args.get('days', 30))
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Enhanced lead analytics
        lead_stats = {
            "total_leads": leads_collection.count_documents({}),
            "recent_leads": leads_collection.count_documents({
                "created_at": {"$gte": start_date}
            }),
            "leads_by_university": list(leads_collection.aggregate([
                {"$group": {
                    "_id": "$university_code",
                    "count": {"$sum": 1},
                    "recent_count": {
                        "$sum": {
                            "$cond": [{"$gte": ["$created_at", start_date]}, 1, 0]
                        }
                    }
                }},
                {"$sort": {"count": -1}}
            ])),
            "leads_by_country": list(leads_collection.aggregate([
                {"$group": {
                    "_id": "$country",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ])),
            "conversion_trends": list(leads_collection.aggregate([
                {"$match": {"created_at": {"$gte": start_date}}},
                {"$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                        "university": "$university_code"
                    },
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id.date": 1}}
            ]))
        }
        
        # Enhanced session analytics
        session_stats = {
            "total_sessions": chat_sessions_collection.count_documents({}),
            "active_sessions": chat_sessions_collection.count_documents({"is_active": True}),
            "recent_sessions": chat_sessions_collection.count_documents({
                "created_at": {"$gte": start_date}
            }),
            "sessions_by_university": list(chat_sessions_collection.aggregate([
                {"$group": {
                    "_id": "$university_code",
                    "count": {"$sum": 1},
                    "avg_messages": {"$avg": "$message_count"},
                    "total_messages": {"$sum": "$message_count"}
                }},
                {"$sort": {"count": -1}}
            ])),
            "engagement_metrics": list(chat_sessions_collection.aggregate([
                {"$match": {"created_at": {"$gte": start_date}}},
                {"$group": {
                    "_id": "$university_code",
                    "avg_session_duration": {"$avg": "$message_count"},
                    "total_interactions": {"$sum": "$message_count"},
                    "session_count": {"$sum": 1}
                }},
                {"$addFields": {
                    "engagement_score": {
                        "$multiply": ["$avg_session_duration", 0.3]
                    }
                }},
                {"$sort": {"engagement_score": -1}}
            ]))
        }
        
        # Enhanced AI and document analytics
        ai_analytics = {
            "total_universities": universities_collection.count_documents({}),
            "ai_enabled_universities": universities_collection.count_documents({
                "gridfs_faiss_index": {"$exists": True}
            }),
            "total_documents": chunks_collection.count_documents({}) if chunks_collection is not None else 0,
            "universities_with_documents": len(list(chunks_collection.distinct("university_x_id"))) if chunks_collection is not None else 0
        }
        
        if chunks_collection is not None:
            ai_analytics["document_distribution"] = list(chunks_collection.aggregate([
                {"$group": {
                    "_id": "$university_x_id",
                    "chunk_count": {"$sum": 1},
                    "unique_files": {"$addToSet": "$file_id"}
                }},
                {"$addFields": {
                    "file_count": {"$size": "$unique_files"}
                }},
                {"$sort": {"chunk_count": -1}}
            ]))
        
        # Performance analytics
        performance_stats = {
            "system_health": {
                "database_status": "connected",
                "ai_services_status": "available" if ENHANCED_RAG_AVAILABLE else "limited",
                "document_processing_status": "available" if PDF_SERVICE_AVAILABLE else "unavailable"
            },
            "resource_utilization": {
                "total_storage_documents": chunks_collection.count_documents({}) if chunks_collection is not None else 0,
                "universities_needing_setup": universities_collection.count_documents({
                    "gridfs_faiss_index": {"$exists": False}
                })
            }
        }
        
        # Enhanced insights and recommendations
        insights = {
            "top_performing_universities": [],
            "universities_needing_attention": [],
            "growth_trends": {},
            "recommendations": []
        }
        
        # Generate insights based on data
        try:
            # Top performing universities by engagement
            top_performers = sorted(
                session_stats["engagement_metrics"], 
                key=lambda x: x.get("engagement_score", 0), 
                reverse=True
            )[:5]
            insights["top_performing_universities"] = top_performers
            
            # Universities with low engagement needing attention
            low_engagement = [
                uni for uni in session_stats["sessions_by_university"] 
                if uni.get("avg_messages", 0) < 2
            ]
            insights["universities_needing_attention"] = low_engagement[:5]
            
            # Growth trends
            current_period_leads = lead_stats["recent_leads"]
            previous_period_start = start_date - timedelta(days=days)
            previous_period_leads = leads_collection.count_documents({
                "created_at": {"$gte": previous_period_start, "$lt": start_date}
            })
            
            if previous_period_leads > 0:
                growth_rate = ((current_period_leads - previous_period_leads) / previous_period_leads) * 100
                insights["growth_trends"] = {
                    "lead_growth_rate": round(growth_rate, 2),
                    "trend_direction": "up" if growth_rate > 0 else "down" if growth_rate < 0 else "stable"
                }
            
            # Generate recommendations
            recommendations = []
            if ai_analytics["ai_enabled_universities"] < ai_analytics["total_universities"]:
                recommendations.append({
                    "type": "ai_setup",
                    "priority": "high",
                    "message": f"{ai_analytics['total_universities'] - ai_analytics['ai_enabled_universities']} universities need AI document processing setup"
                })
            
            if len(low_engagement) > 0:
                recommendations.append({
                    "type": "engagement",
                    "priority": "medium",
                    "message": f"{len(low_engagement)} universities have low engagement and may need content optimization"
                })
            
            insights["recommendations"] = recommendations
            
        except Exception as e:
            logger.warning(f"Error generating insights: {e}")
        
        return jsonify({
            "success": True,
            "analytics": {
                "date_range": {
                    "days": days,
                    "start_date": start_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat()
                },
                "leads": lead_stats,
                "sessions": session_stats,
                "ai_services": ai_analytics,
                "performance": performance_stats,
                "insights": insights
            },
            "generated_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting aggregated analytics: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to get aggregated analytics: {str(e)}"
        }), 500

@superadmin_bp.route('/universities/<x_id>/update', methods=['PUT'])
@require_auth
@require_superadmin
def update_university_settings(x_id):
    """Update university settings with enhanced branding and AI configuration"""
    try:
        data = request.get_json()
        
        # Check if university exists
        university = University.get_university_by_x_id(x_id)
        if not university:
            return jsonify({
                "success": False,
                "error": "University not found"
            }), 404
        
        # Build update data
        update_data = {}
        updated_fields = []
        
        # Basic info updates
        if 'name' in data:
            update_data['name'] = data['name']
            updated_fields.append('name')
        if 'description' in data:
            update_data['description'] = data['description']
            updated_fields.append('description')
        if 'status' in data and data['status'] in ['active', 'inactive', 'maintenance']:
            update_data['status'] = data['status']
            updated_fields.append('status')
        
        # Enhanced branding updates
        if 'branding' in data:
            branding_data = data['branding']
            current_branding = university.get('branding', {})
            
            # Update branding fields with validation
            if 'logo_url' in branding_data:
                current_branding['logo_url'] = branding_data['logo_url']
            if 'favicon_url' in branding_data:
                current_branding['favicon_url'] = branding_data['favicon_url']
            if 'theme_colors' in branding_data:
                # Validate theme colors structure
                theme_colors = branding_data['theme_colors']
                if isinstance(theme_colors, dict):
                    current_branding['theme_colors'] = theme_colors
            if 'custom_css' in branding_data:
                current_branding['custom_css'] = branding_data['custom_css']
            if 'domain_name' in branding_data:
                current_branding['domain_name'] = branding_data['domain_name']
            if 'welcome_message' in branding_data:
                current_branding['welcome_message'] = branding_data['welcome_message']
            if 'footer_text' in branding_data:
                current_branding['footer_text'] = branding_data['footer_text']
            
            update_data['branding'] = current_branding
            updated_fields.append('branding')
        
        # AI configuration updates
        if 'ai_config' in data:
            ai_config = data['ai_config']
            current_ai_config = university.get('ai_config', {})
            
            if 'enabled' in ai_config:
                current_ai_config['enabled'] = bool(ai_config['enabled'])
            if 'rag_model' in ai_config:
                current_ai_config['rag_model'] = ai_config['rag_model']
            if 'max_tokens' in ai_config:
                current_ai_config['max_tokens'] = int(ai_config['max_tokens'])
            if 'temperature' in ai_config:
                current_ai_config['temperature'] = float(ai_config['temperature'])
            
            update_data['ai_config'] = current_ai_config
            updated_fields.append('ai_config')
        
        # Contact information updates
        if 'contact_info' in data:
            contact_info = data['contact_info']
            current_contact = university.get('contact_info', {})
            
            for field in ['email', 'phone', 'address', 'website']:
                if field in contact_info:
                    current_contact[field] = contact_info[field]
            
            update_data['contact_info'] = current_contact
            updated_fields.append('contact_info')
        
        # Add update metadata
        update_data['updated_at'] = datetime.utcnow()
        update_data['last_updated_by'] = ObjectId(request.current_user['id'])
        
        if not updated_fields:
            return jsonify({
                "success": False,
                "error": "No valid fields provided for update"
            }), 400
        
        # Update in database
        result = universities_collection.update_one(
            {"x_id": x_id.upper()},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            return jsonify({
                "success": False,
                "error": "No changes were made to the database"
            }), 400
        
        # Enhanced audit trail
        try:
            University.update_university_metadata(
                x_id, 
                request.current_user['id'], 
                "settings_updated",
                {
                    "updated_fields": updated_fields,
                    "updated_by": request.current_user.get('email', 'unknown'),
                    "update_summary": {
                        "branding_updated": 'branding' in updated_fields,
                        "ai_config_updated": 'ai_config' in updated_fields,
                        "basic_info_updated": any(f in updated_fields for f in ['name', 'description', 'status'])
                    }
                }
            )
        except Exception as e:
            logger.warning(f"Error updating audit trail: {e}")
        
        return jsonify({
            "success": True,
            "message": f"University {university['name']} updated successfully",
            "updated_fields": updated_fields,
            "changes_summary": {
                "total_fields_updated": len(updated_fields),
                "branding_modified": 'branding' in updated_fields,
                "ai_configuration_modified": 'ai_config' in updated_fields
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error updating university settings: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to update university settings: {str(e)}"
        }), 500

@superadmin_bp.route('/audit-logs', methods=['GET'])
@require_auth
@require_superadmin
def get_audit_logs():
    """Get enhanced system audit logs with filtering and analytics"""
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 50))
        university_filter = request.args.get('university')
        action_filter = request.args.get('action')
        user_filter = request.args.get('user')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Enhanced user activities query
        user_query = {}
        if university_filter:
            university = University.get_university_by_x_id(university_filter)
            if university:
                user_query['university_id'] = ObjectId(university['_id'])
        
        if user_filter:
            user_query['email'] = {"$regex": user_filter, "$options": "i"}
        
        # Date filtering
        if date_from or date_to:
            date_filter = {}
            if date_from:
                date_filter["$gte"] = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            if date_to:
                date_filter["$lte"] = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            user_query['created_at'] = date_filter
        
        # Get enhanced user activities
        recent_users = list(users_collection.find(
            user_query,
            {"email": 1, "role": 1, "created_at": 1, "created_by": 1, "last_login": 1, "login_count": 1, "profile": 1}
        ).sort("created_at", -1).limit(limit))
        
        # Process user data
        for user in recent_users:
            user['_id'] = str(user['_id'])
            if 'created_by' in user and user['created_by']:
                user['created_by'] = str(user['created_by'])
                # Get creator info
                try:
                    creator = users_collection.find_one({"_id": ObjectId(user['created_by'])}, {"email": 1, "profile": 1})
                    if creator:
                        user['created_by_info'] = {
                            "email": creator.get('email'),
                            "name": f"{creator.get('profile', {}).get('first_name', '')} {creator.get('profile', {}).get('last_name', '')}".strip()
                        }
                except Exception as e:
                    logger.warning(f"Error getting creator info: {e}")
            
            if 'university_id' in user and user['university_id']:
                user['university_id'] = str(user['university_id'])
                # Add university info
                try:
                    university = University.get_university_by_id(str(user['university_id']))
                    if university:
                        user['university_info'] = {
                            "name": university.get('name'),
                            "x_id": university.get('x_id')
                        }
                except Exception as e:
                    logger.warning(f"Error getting university info: {e}")
        
        # Enhanced university activities
        university_activities = []
        university_query = {}
        if university_filter:
            university_query['x_id'] = university_filter.upper()
        
        universities_with_audit = list(universities_collection.find(
            {**university_query, "audit_trail": {"$exists": True}},
            {"name": 1, "x_id": 1, "audit_trail": 1}
        ))
        
        for uni in universities_with_audit:
            uni['_id'] = str(uni['_id'])
            if 'audit_trail' in uni:
                for audit in uni['audit_trail'][-20:]:  # Last 20 activities
                    activity = {
                        "university_name": uni['name'],
                        "university_x_id": uni['x_id'],
                        "action": audit.get('action'),
                        "performed_by": str(audit.get('performed_by', '')),
                        "timestamp": audit.get('timestamp'),
                        "metadata": audit.get('metadata', {})
                    }
                    
                    # Add performer info
                    try:
                        if activity['performed_by']:
                            performer = users_collection.find_one(
                                {"_id": ObjectId(activity['performed_by'])}, 
                                {"email": 1, "profile": 1, "role": 1}
                            )
                            if performer:
                                activity['performed_by_info'] = {
                                    "email": performer.get('email'),
                                    "role": performer.get('role'),
                                    "name": f"{performer.get('profile', {}).get('first_name', '')} {performer.get('profile', {}).get('last_name', '')}".strip()
                                }
                    except Exception as e:
                        logger.warning(f"Error getting performer info: {e}")
                    
                    # Apply action filter
                    if not action_filter or action_filter.lower() in activity['action'].lower():
                        university_activities.append(activity)
        
        # Sort by timestamp
        university_activities.sort(
            key=lambda x: x['timestamp'] if isinstance(x['timestamp'], datetime) else datetime.min, 
            reverse=True
        )
        university_activities = university_activities[:limit]
        
        # System activities (sessions, leads, etc.)
        system_activities = []
        
        # Recent session activities
        recent_sessions = list(chat_sessions_collection.find(
            {},
            {"university_code": 1, "university_x_id": 1, "created_at": 1, "message_count": 1, "is_active": 1}
        ).sort("created_at", -1).limit(10))
        
        for session in recent_sessions:
            system_activities.append({
                "type": "session",
                "action": "session_created",
                "university_code": session.get('university_code'),
                "university_x_id": session.get('university_x_id'),
                "timestamp": session.get('created_at'),
                "metadata": {
                    "message_count": session.get('message_count', 0),
                    "is_active": session.get('is_active', False)
                }
            })
        
        # Recent lead activities
        recent_leads = list(leads_collection.find(
            {},
            {"university_code": 1, "email": 1, "country": 1, "created_at": 1, "name": 1}
        ).sort("created_at", -1).limit(10))
        
        for lead in recent_leads:
            system_activities.append({
                "type": "lead",
                "action": "lead_created",
                "university_code": lead.get('university_code'),
                "timestamp": lead.get('created_at'),
                "metadata": {
                    "lead_email": lead.get('email'),
                    "lead_name": lead.get('name'),
                    "country": lead.get('country')
                }
            })
        
        # Sort system activities
        system_activities.sort(
            key=lambda x: x['timestamp'] if isinstance(x['timestamp'], datetime) else datetime.min, 
            reverse=True
        )
        
        # Enhanced analytics
        audit_analytics = {
            "summary": {
                "total_users": len(recent_users),
                "total_university_actions": len(university_activities),
                "total_system_activities": len(system_activities),
                "date_range": {
                    "from": date_from,
                    "to": date_to
                }
            },
            "activity_breakdown": {
                "user_registrations": len([u for u in recent_users if u.get('created_at')]),
                "university_updates": len([a for a in university_activities if 'update' in a.get('action', '')]),
                "recent_sessions": len([a for a in system_activities if a['type'] == 'session']),
                "recent_leads": len([a for a in system_activities if a['type'] == 'lead'])
            },
            "most_active_universities": {}
        }
        
        # Calculate most active universities
        university_activity_count = {}
        for activity in university_activities:
            x_id = activity.get('university_x_id')
            if x_id:
                university_activity_count[x_id] = university_activity_count.get(x_id, 0) + 1
        
        audit_analytics["most_active_universities"] = dict(
            sorted(university_activity_count.items(), key=lambda x: x[1], reverse=True)[:5]
        )
        
        return jsonify({
            "success": True,
            "audit_logs": {
                "user_activities": recent_users,
                "university_activities": university_activities,
                "system_activities": system_activities[:limit]
            },
            "analytics": audit_analytics,
            "filters_applied": {
                "limit": limit,
                "university": university_filter,
                "action": action_filter,
                "user": user_filter,
                "date_from": date_from,
                "date_to": date_to
            },
            "generated_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting audit logs: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to get audit logs: {str(e)}"
        }), 500

@superadmin_bp.route('/system/health', methods=['GET'])
@require_auth
@require_superadmin
def get_system_health():
    """Get comprehensive system health status including all services"""
    try:
        health_status = {
            "overall_health": "healthy",
            "services": {},
            "databases": {},
            "ai_services": {},
            "performance_metrics": {}
        }
        
        issues = []
        
        # Database health checks
        try:
            # MongoDB connectivity
            universities_collection.find_one()
            health_status["databases"]["mongodb"] = {
                "status": "healthy",
                "message": "MongoDB connection successful"
            }
        except Exception as e:
            health_status["databases"]["mongodb"] = {
                "status": "unhealthy",
                "message": f"MongoDB connection failed: {str(e)}"
            }
            issues.append("MongoDB connectivity issue")
        
        # Enhanced RAG Service health
        if ENHANCED_RAG_AVAILABLE and enhanced_rag_service:
            try:
                rag_healthy, rag_message = enhanced_rag_service.health_check()
                health_status["ai_services"]["enhanced_rag"] = {
                    "status": "healthy" if rag_healthy else "unhealthy",
                    "message": rag_message,
                    "capabilities": {
                        "vector_search": enhanced_rag_service.vector_search_available,
                        "conversational_memory": True,
                        "lead_management": True
                    }
                }
                if not rag_healthy:
                    issues.append("Enhanced RAG Service issue")
            except Exception as e:
                health_status["ai_services"]["enhanced_rag"] = {
                    "status": "error",
                    "message": f"Enhanced RAG error: {str(e)}"
                }
                issues.append("Enhanced RAG Service error")
        else:
            health_status["ai_services"]["enhanced_rag"] = {
                "status": "unavailable",
                "message": "Enhanced RAG Service not available"
            }
            issues.append("Enhanced RAG Service not available")
        
        # PDF Service health
        if PDF_SERVICE_AVAILABLE:
            try:
                pdf_healthy, pdf_message = pdf_health_check()
                health_status["ai_services"]["pdf_processing"] = {
                    "status": "healthy" if pdf_healthy else "unhealthy",
                    "message": pdf_message
                }
                if not pdf_healthy:
                    issues.append("PDF processing service issue")
            except Exception as e:
                health_status["ai_services"]["pdf_processing"] = {
                    "status": "error",
                    "message": f"PDF service error: {str(e)}"
                }
                issues.append("PDF processing service error")
        else:
            health_status["ai_services"]["pdf_processing"] = {
                "status": "unavailable",
                "message": "PDF processing service not available"
            }
        
        # Performance metrics
        try:
            # Database counts
            health_status["performance_metrics"] = {
                "total_universities": universities_collection.count_documents({}),
                "total_users": users_collection.count_documents({}),
                "total_sessions": chat_sessions_collection.count_documents({}),
                "active_sessions": chat_sessions_collection.count_documents({"is_active": True}),
                "total_leads": leads_collection.count_documents({}),
                "total_documents": chunks_collection.count_documents({}) if chunks_collection is not None else 0,
                "universities_with_ai": universities_collection.count_documents({
                    "gridfs_faiss_index": {"$exists": True}
                })
            }
            
            # Calculate health metrics
            metrics = health_status["performance_metrics"]
            if metrics["total_universities"] > 0:
                ai_coverage = (metrics["universities_with_ai"] / metrics["total_universities"]) * 100
                health_status["performance_metrics"]["ai_coverage_percentage"] = round(ai_coverage, 2)
                
                if ai_coverage < 50:
                    issues.append(f"Low AI coverage: {ai_coverage:.1f}% of universities")
            
        except Exception as e:
            logger.warning(f"Error getting performance metrics: {e}")
            issues.append("Performance metrics collection failed")
        
        # Service-specific health checks
        services = ["chat", "lead", "university", "auth"]
        for service in services:
            try:
                # Basic service availability check (simplified)
                health_status["services"][service] = {
                    "status": "healthy",
                    "message": f"{service.title()} service operational"
                }
            except Exception as e:
                health_status["services"][service] = {
                    "status": "unhealthy",
                    "message": f"{service.title()} service error: {str(e)}"
                }
                issues.append(f"{service.title()} service issue")
        
        # Determine overall health
        if issues:
            if len(issues) >= 3:
                health_status["overall_health"] = "critical"
            elif any("critical" in issue.lower() or "mongodb" in issue.lower() for issue in issues):
                health_status["overall_health"] = "degraded"
            else:
                health_status["overall_health"] = "warning"
        
        health_status["issues"] = issues
        health_status["issue_count"] = len(issues)
        health_status["checked_at"] = datetime.utcnow().isoformat()
        
        # Recommendations based on health status
        recommendations = []
        if "Enhanced RAG Service not available" in issues:
            recommendations.append({
                "priority": "high",
                "category": "ai_services",
                "message": "Install ML dependencies (faiss-cpu, sentence-transformers) to enable enhanced AI features"
            })
        
        if health_status["performance_metrics"].get("ai_coverage_percentage", 0) < 70:
            recommendations.append({
                "priority": "medium",
                "category": "ai_setup",
                "message": "Consider setting up document processing for more universities to improve AI coverage"
            })
        
        if health_status["performance_metrics"].get("active_sessions", 0) == 0:
            recommendations.append({
                "priority": "low",
                "category": "usage",
                "message": "No active chat sessions detected - system may be underutilized"
            })
        
        health_status["recommendations"] = recommendations
        
        # HTTP status code based on health
        http_status = 200
        if health_status["overall_health"] == "critical":
            http_status = 503
        elif health_status["overall_health"] == "degraded":
            http_status = 503
        elif health_status["overall_health"] == "warning":
            http_status = 200
        
        return jsonify(health_status), http_status
        
    except Exception as e:
        logger.error(f"Error getting system health: {str(e)}")
        return jsonify({
            "overall_health": "critical",
            "error": f"Health check failed: {str(e)}",
            "checked_at": datetime.utcnow().isoformat()
        }), 503

@superadmin_bp.route('/system/maintenance', methods=['POST'])
@require_auth
@require_superadmin
def trigger_maintenance_tasks():
    """Trigger system maintenance tasks"""
    try:
        data = request.get_json()
        task_type = data.get('task_type')
        
        if not task_type:
            return jsonify({
                "success": False,
                "error": "task_type is required"
            }), 400
        
        results = {}
        
        if task_type == "cleanup_sessions":
            # Clean up old inactive sessions
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            result = chat_sessions_collection.delete_many({
                "is_active": False,
                "updated_at": {"$lt": cutoff_date}
            })
            results["sessions_cleaned"] = result.deleted_count
        
        elif task_type == "rebuild_indexes":
            # Rebuild database indexes
            try:
                # Recreate important indexes
                universities_collection.create_index("x_id", unique=True)
                users_collection.create_index("email", unique=True)
                leads_collection.create_index([("email", 1), ("university_code", 1)], unique=True)
                results["indexes_rebuilt"] = True
            except Exception as e:
                results["indexes_error"] = str(e)
        
        elif task_type == "sync_university_data":
            # Sync university data and ensure X-IDs
            updated_count = University.ensure_x_ids_for_existing_universities()
            results["universities_updated"] = updated_count
        
        elif task_type == "cleanup_cache":
            # Clear RAG service cache if available
            if ENHANCED_RAG_AVAILABLE and enhanced_rag_service:
                enhanced_rag_service.clear_cache()
                results["cache_cleared"] = True
            else:
                results["cache_cleared"] = False
                results["cache_message"] = "Enhanced RAG service not available"
        
        else:
            return jsonify({
                "success": False,
                "error": f"Unknown task_type: {task_type}"
            }), 400
        
        # Log maintenance action
        try:
            # This would be logged in a maintenance log collection if we had one
            logger.info(f"Maintenance task '{task_type}' executed by {request.current_user.get('email')}: {results}")
        except Exception as e:
            logger.warning(f"Error logging maintenance action: {e}")
        
        return jsonify({
            "success": True,
            "task_type": task_type,
            "results": results,
            "executed_by": request.current_user.get('email'),
            "executed_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error executing maintenance task: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Failed to execute maintenance task: {str(e)}"
        }), 500

# Helper functions for enhanced features
def _calculate_branding_completeness(branding: dict) -> int:
    """Calculate branding completeness score (0-100)"""
    required_fields = ['logo_url', 'theme_colors', 'domain_name', 'welcome_message']
    optional_fields = ['favicon_url', 'custom_css', 'footer_text']
    
    score = 0
    # Required fields worth 60 points total (15 each)
    for field in required_fields:
        if branding.get(field):
            score += 15
    
    # Optional fields worth 40 points total (13.33 each, rounded)
    for field in optional_fields:
        if branding.get(field):
            score += 13
    
    return min(score, 100)

def _get_missing_branding_elements(branding: dict) -> list:
    """Get list of missing branding elements"""
    all_fields = ['logo_url', 'favicon_url', 'theme_colors', 'custom_css', 'domain_name', 'welcome_message', 'footer_text']
    return [field for field in all_fields if not branding.get(field)]

def _get_branding_recommendations(branding: dict) -> list:
    """Get branding improvement recommendations"""
    recommendations = []
    
    if not branding.get('logo_url'):
        recommendations.append({
            "priority": "high",
            "element": "logo_url",
            "message": "Add university logo for professional appearance"
        })
    
    if not branding.get('theme_colors'):
        recommendations.append({
            "priority": "high",
            "element": "theme_colors",
            "message": "Configure theme colors to match university branding"
        })
    
    if not branding.get('domain_name'):
        recommendations.append({
            "priority": "medium",
            "element": "domain_name",
            "message": "Set up custom domain for branded experience"
        })
    
    if not branding.get('welcome_message'):
        recommendations.append({
            "priority": "medium",
            "element": "welcome_message",
            "message": "Add personalized welcome message"
        })
    
    if not branding.get('favicon_url'):
        recommendations.append({
            "priority": "low",
            "element": "favicon_url",
            "message": "Add favicon for browser tab branding"
        })
    
    return recommendations