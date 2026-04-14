from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import users_collection
from datetime import datetime, timedelta
import jwt
import os
from bson import ObjectId
from app.utils.rbac import Roles

auth_bp = Blueprint('auth', __name__)

# JWT Secret Key - in production, this should be in environment variables
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user (admin or student)"""
    try:
        print("=== DEBUG: Starting registration ===")
        print(f"=== DEBUG: Content-Type: {request.content_type} ===")
        print(f"=== DEBUG: Raw data: {request.get_data()} ===")
        data = request.get_json()
        print(f"=== DEBUG: Received data: {data} ===")
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', Roles.STUDENT)  # Default to student
        university_id = data.get('universityId')  # This should be X-ID
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
        
        if role not in [Roles.ADMIN, Roles.STUDENT, Roles.SUPERADMIN]:
            return jsonify({"error": "Invalid role. Must be 'admin', 'student', or 'superadmin'"}), 400
        
        # Check if user already exists
        existing_user = users_collection.find_one({"email": email.lower()})
        if existing_user:
            return jsonify({"error": "User with this email already exists"}), 409
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        # Create user document
        user_data = {
            "email": email.lower(),
            "password_hash": password_hash,
            "role": role,
            "created_at": datetime.utcnow(),
            "is_active": True,
            # Multi-university support fields
            "universities": [],  # Array of university IDs for multi-university access
            "created_by": None,  # User ID of who created this user (for sub-admins)
            "permissions": [],  # Array of specific permissions
            "last_login": None,  # Track last login time
            "profile": {
                "first_name": "",
                "last_name": "",
                "phone": "",
                "timezone": "UTC"
            }
        }
        
        # Add university assignment for admin users
        if role == Roles.ADMIN and university_id:
            # Get university details by X-ID
            from app.models.university import University
            university = University.get_university_by_x_id(university_id)
            if university:
                user_data['university_x_id'] = university_id
                user_data['university_code'] = university['code']
                print(f"=== DEBUG: Assigned admin to university {university['name']} ({university_id}) ===")
            else:
                return jsonify({"error": f"University with X-ID '{university_id}' not found"}), 400
        elif role == Roles.ADMIN and not university_id:
            return jsonify({"error": "University X-ID is required for admin users"}), 400

        # Superadmins don't need university assignment (they can access all)
        if role == Roles.SUPERADMIN:
            user_data['universities'] = []  # Empty array, can be populated later
        
        # Insert user
        result = users_collection.insert_one(user_data)
        user_id = str(result.inserted_id)
        
        # Generate JWT token
        token = generate_jwt_token(user_id, email, role)
        
        # Return user info (without password hash) - UPDATED
        user_info = {
            "_id": user_id,
            "email": email.lower(),
            "role": role
        }
        
        # Add university fields for admin users
        if role == Roles.ADMIN and university_id:
            user_info['university_x_id'] = university_id
            user_info['university_code'] = user_data.get('university_code')
        
        return jsonify({
            "token": token,
            "user": user_info,
            "message": "User registered successfully"
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
        
        # Find user by email
        user = users_collection.find_one({"email": email.lower()})
        if not user:
            return jsonify({"message": "Invalid email or password"}), 401
        
        # Check password
        if not check_password_hash(user['password_hash'], password):
            return jsonify({"message": "Invalid email or password"}), 401
        
        # Check if user is active
        if not user.get('is_active', True):
            return jsonify({"message": "Account is deactivated"}), 401
        
        # Generate JWT token
        user_id = str(user['_id'])
        token = generate_jwt_token(user_id, user['email'], user['role'])
        
        # Return user info (without password hash)
        user_info = {
            "_id": user_id,
            "email": user['email'],
            "role": user['role'],
            "university_x_id": user.get('university_x_id'),
            "university_code": user.get('university_code')
        }
        
        # Fix: Convert ObjectId to string for JSON serialization
        if 'university_id' in user and user['university_id']:
            user_info['universityId'] = str(user['university_id'])

            # ✅ FIX: Add profile information with ObjectIds converted
        if 'profile' in user:
            user_info['profile'] = user['profile']
        
        # ✅ FIX: Handle created_by field if it exists
        if 'created_by' in user and user['created_by']:
            user_info['created_by'] = str(user['created_by'])
        
        # Update last login timestamp
        users_collection.update_one(
            {"_id": user['_id']},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        return jsonify({
            "token": token,
            "user": user_info,
            "message": "Login successful"
        })
        
    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500

@auth_bp.route('/verify', methods=['GET'])
def verify_token():
    """Verify JWT token"""
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "No token provided"}), 401
        
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Decode token
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = payload['user_id']
        
        # Get user from database
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user or not user.get('is_active', True):
            return jsonify({"error": "Invalid token"}), 401
        
        # Return user info
        user_info = {
            "_id": str(user['_id']),
            "email": user['email'],
            "role": user['role'],
            "university_x_id": user.get('university_x_id'),
            "university_code": user.get('university_code')
        }
        
        # Fix: Convert ObjectId to string for JSON serialization
        if 'university_id' in user and user['university_id']:
            user_info['universityId'] = str(user['university_id'])
        
        return jsonify({"user": user_info})
        
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"error": f"Token verification failed: {str(e)}"}), 500

def generate_jwt_token(user_id, email, role):
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.utcnow() + timedelta(days=7),  # Token expires in 7 days
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256') 

# # Add this to auth_routes.py temporarily
# @auth_bp.route('/migrate-admin', methods=['POST'])
# def migrate_admin():
#     from bson import ObjectId
    
#     result = users_collection.update_one(
#         {"_id": ObjectId("68651a27cacff6da58b9a90b")},
#         {"$set": {
#             "university_x_id": "XNR35QWNP",
#             "university_code": "csss"
#         }}
#     )
    
#     return jsonify({
#         "success": True,
#         "updated": result.modified_count > 0,
#         "message": f"Updated {result.modified_count} user(s)"
#     })

