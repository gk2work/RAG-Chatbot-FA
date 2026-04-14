# app/utils/rbac.py
"""
Role-Based Access Control (RBAC) utilities for SuperAdmin implementation
"""

from functools import wraps
from flask import request, jsonify
import jwt
import os
from app.models import users_collection
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

# JWT Secret Key - should match across all auth modules
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')

class Roles:
    """Role definitions with hierarchy"""
    SUPERADMIN = 'superadmin'
    ADMIN = 'admin'
    STUDENT = 'student'
    
    # Role hierarchy - higher roles inherit lower role permissions
    HIERARCHY = {
        'superadmin': ['superadmin', 'admin', 'student'],
        'admin': ['admin', 'student'],
        'student': ['student']
    }
    
    @classmethod
    def can_access(cls, user_role, required_role):
        """Check if user_role can access required_role level"""
        if user_role not in cls.HIERARCHY:
            return False
        return required_role in cls.HIERARCHY[user_role]
    
    @classmethod
    def get_allowed_roles(cls, user_role):
        """Get all roles that user_role can access"""
        return cls.HIERARCHY.get(user_role, [])

def decode_jwt_token(token):
    """Helper function to decode JWT token"""
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "Token has expired"
    except jwt.InvalidTokenError:
        return None, "Invalid authentication token"
    except Exception as e:
        return None, f"Authentication failed: {str(e)}"

def get_user_from_token(token):
    """Get user information from JWT token"""
    payload, error = decode_jwt_token(token)
    if error:
        return None, error
    
    try:
        user_id = payload['user_id']
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        
        if not user or not user.get('is_active', True):
            return None, "Invalid or inactive user"
        
        user_info = {
            'id': user_id,
            'email': user['email'],
            'role': user['role'],
            'university_id': str(user['university_id']) if user.get('university_id') else None,
            'universities': user.get('universities', [])  # For superadmin multi-university access
        }
        
        # ✅ CRITICAL: Add university context for admin users
        if user['role'] == 'admin':
            user_info['university_x_id'] = user.get('university_x_id')
            user_info['university_code'] = user.get('university_code')

            if 'university_id' in user and user['university_id']:
                user_info['university_id'] = str(user['university_id'])

        # ✅ Convert any other ObjectId fields that might exist
        if 'created_by' in user and user.get('created_by'):
            user_info['created_by'] = str(user['created_by'])
        
        return user_info, None
    except Exception as e:
        return None, f"Failed to get user info: {str(e)}"

# Enhanced decorators with role hierarchy support

def require_auth(f):
    """Basic authentication decorator - requires valid JWT token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({"error": "Authentication token required"}), 401
            
            user_info, error = get_user_from_token(token)
            if error:
                return jsonify({"error": error}), 401
            
            # Add user info to request context
            request.current_user = user_info
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return jsonify({"error": f"Authentication failed: {str(e)}"}), 500
    
    return decorated_function

def require_role(required_role):
    """Decorator factory for role-based access control"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({"error": "Authentication required"}), 401
            
            user_role = request.current_user.get('role')
            if not Roles.can_access(user_role, required_role):
                return jsonify({
                    "error": f"Insufficient permissions. {required_role.title()} role or higher required."
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_superadmin(f):
    """Decorator to require superadmin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(request, 'current_user'):
            return jsonify({"error": "Authentication required"}), 401
        
        user_role = request.current_user.get('role')
        if user_role != Roles.SUPERADMIN:
            return jsonify({"error": "Superadmin access required"}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_admin_or_above(f):
    """Decorator to require admin or superadmin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(request, 'current_user'):
            return jsonify({"error": "Authentication required"}), 401
        
        user_role = request.current_user.get('role')
        if not Roles.can_access(user_role, Roles.ADMIN):
            return jsonify({"error": "Admin access or higher required"}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_student_or_above(f):
    """Decorator to require student, admin, or superadmin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(request, 'current_user'):
            return jsonify({"error": "Authentication required"}), 401
        
        user_role = request.current_user.get('role')
        if not Roles.can_access(user_role, Roles.STUDENT):
            return jsonify({"error": "Valid user role required"}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_university_access(university_x_id=None):
    """
    Decorator to ensure user has access to specific university
    - Superadmins have access to all universities
    - Admins only have access to their assigned university
    - Students only have access to their assigned university
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({"error": "Authentication required"}), 401
            
            user_role = request.current_user.get('role')
            
            # Superadmins have access to all universities
            if user_role == Roles.SUPERADMIN:
                return f(*args, **kwargs)
            
            # Get university X-ID from URL parameter or function parameter
            target_x_id = university_x_id or kwargs.get('x_id') or request.view_args.get('x_id')
            
            if not target_x_id:
                return jsonify({"error": "University identifier required"}), 400
            
            # For admins and students, check university assignment
            user_university_id = request.current_user.get('university_id')
            user_universities = request.current_user.get('universities', [])
            
            # Import here to avoid circular imports
            from app.models.university import University
            
            # Get university by X-ID to check permissions
            university = University.get_university_by_x_id(target_x_id)
            if not university:
                return jsonify({"error": "University not found"}), 404
            
            university_id = str(university['_id'])
            
            # Check if user has access to this university
            has_access = False
            
            if user_university_id and str(user_university_id) == university_id:
                has_access = True
            elif university_id in user_universities:
                has_access = True
            
            if not has_access:
                return jsonify({
                    "error": "Access denied. You don't have permission to access this university."
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def filter_by_university_access(query_filter=None):
    """
    Helper function to filter database queries based on user's university access
    Returns updated filter that respects user permissions
    """
    if not hasattr(request, 'current_user'):
        return {}
    
    user_role = request.current_user.get('role')
    
    # Superadmins can see all data
    if user_role == Roles.SUPERADMIN:
        return query_filter or {}
    
    # For admins and students, filter by their university access
    user_university_id = request.current_user.get('university_id')
    user_universities = request.current_user.get('universities', [])
    
    # Build university filter
    university_filter = {}
    if user_university_id:
        if user_universities:
            # User has access to multiple universities
            all_universities = [user_university_id] + user_universities
            university_filter = {"university_id": {"$in": all_universities}}
        else:
            # User has access to single university
            university_filter = {"university_id": user_university_id}
    
    # Combine with existing filter
    if query_filter:
        return {"$and": [query_filter, university_filter]}
    else:
        return university_filter

# Utility functions for role management

def is_superadmin(user_role):
    """Check if user is superadmin"""
    return user_role == Roles.SUPERADMIN

def is_admin_or_above(user_role):
    """Check if user is admin or superadmin"""
    return Roles.can_access(user_role, Roles.ADMIN)

def get_user_permissions(user_role):
    """Get list of permissions for a user role"""
    return {
        'can_create_universities': user_role == Roles.SUPERADMIN,
        'can_manage_users': user_role in [Roles.SUPERADMIN, Roles.ADMIN],
        'can_view_all_universities': user_role == Roles.SUPERADMIN,
        'can_upload_documents': user_role in [Roles.SUPERADMIN, Roles.ADMIN],
        'can_view_analytics': user_role in [Roles.SUPERADMIN, Roles.ADMIN],
        'can_chat': True,  # All users can chat
        'allowed_roles': Roles.get_allowed_roles(user_role)
    }