from app.models import universities_collection, documents_collection
from bson import ObjectId
from datetime import datetime
import hashlib
import base64
import logging

class University:
    @staticmethod
    def generate_x_id(university_code):
        """
        Generate a deterministic 8-character alphanumeric X ID based on university_code
        This ensures the same university always gets the same X ID
        """
        # Create hash of university_code
        hash_object = hashlib.sha256(university_code.encode())
        hash_hex = hash_object.hexdigest()
        
        # Convert to base64 and take first 8 alphanumeric characters
        hash_b64 = base64.b64encode(bytes.fromhex(hash_hex)).decode('ascii')
        
        # Filter to alphanumeric only and take first 8 characters
        x_id = ''.join(c for c in hash_b64 if c.isalnum())[:8].upper()
        
        return f"X{x_id}"
    
    @staticmethod
    def get_university_count():
        """Get total count of universities"""
        try:
            return universities_collection.count_documents({})
        except Exception as e:
            logging.error(f"Error getting university count: {e}")
            return 0
    
    @staticmethod
    def get_universities_created_today():
        """Get count of universities created today"""
        try:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            return universities_collection.count_documents({
                "created_at": {"$gte": today}
            })
        except Exception as e:
            logging.error(f"Error getting universities created today: {e}")
            return 0
    
    @staticmethod
    def create_university(name, code, description=""):
        """Create a new university with X-ID"""
        # Generate X-ID for the university
        x_id = University.generate_x_id(code)
        
        university_data = {
            "name": name,
            "code": code.lower(),
            "x_id": x_id,  # Store X-ID in database
            "description": description,
            "created_at": datetime.utcnow(),
            "document_count": 0,
            "branding": {
                "logo_url": "",
                "theme_colors": {
                    "primary": "#1976d2",
                    "secondary": "#dc004e",
                    "accent": "#82b1ff"
                },
                "custom_css": "",
                "domain_name": "",
                "favicon_url": ""
                 },
            "contact_info": {
                "email": "",
                "phone": "",
                "address": ""
            },
            "settings": {
                "chatbot_enabled": True,
                "lead_capture_enabled": True,
                "analytics_enabled": True
            },
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.utcnow(),
                "updated_by": None,
                "audit_trail": []
            }
        }
        
        result = universities_collection.insert_one(university_data)
        return str(result.inserted_id)
    
    @staticmethod
    def get_university_by_code(code):
        """Get university by code"""
        return universities_collection.find_one({"code": code.lower()})
    
    @staticmethod
    def get_university_by_x_id(x_id):
        """Get university by X-ID"""
        return universities_collection.find_one({"x_id": x_id.upper()})
    
    @staticmethod
    def get_all_universities():
        """Get all universities with X-IDs included"""
        universities = list(universities_collection.find())
        
        # Ensure all universities have X-IDs (for backward compatibility)
        for uni in universities:
            if 'x_id' not in uni or not uni['x_id']:
                # Generate X-ID if missing
                uni['x_id'] = University.generate_x_id(uni.get('code', ''))
                # Update in database
                universities_collection.update_one(
                    {"_id": uni['_id']},
                    {"$set": {"x_id": uni['x_id']}}
                )
        
        return universities
    
    @staticmethod
    def add_document_to_university(university_code, document_data):
        """Add document to university and associate with X-ID"""
        # Get university to ensure it exists and get X-ID
        university = University.get_university_by_code(university_code)
        if not university:
            raise ValueError(f"University with code '{university_code}' not found")
        
        # Generate X-ID if not present (backward compatibility)
        x_id = university.get('x_id')
        if not x_id:
            x_id = University.generate_x_id(university_code)
            # Update university with X-ID
            universities_collection.update_one(
                {"code": university_code.lower()},
                {"$set": {"x_id": x_id}}
            )
        
        document = {
            "university_code": university_code.lower(),
            "university_x_id": x_id,  # Store X-ID reference
            "title": document_data.get("title"),
            "content": document_data.get("content"),
            "document_type": document_data.get("type", "text"),
            "metadata": document_data.get("metadata", {}),
            "created_at": datetime.utcnow()
        }
        result = documents_collection.insert_one(document)
        
        # Update document count
        universities_collection.update_one(
            {"code": university_code.lower()},
            {"$inc": {"document_count": 1}}
        )
        
        return str(result.inserted_id)
    
    @staticmethod
    def get_university_documents(university_code):
        """Get all documents for a university by code"""
        return list(documents_collection.find({"university_code": university_code.lower()}))
    
    @staticmethod
    def get_university_documents_by_x_id(x_id):
        """Get all documents for a university by X-ID"""
        return list(documents_collection.find({"university_x_id": x_id.upper()}))
    
    @staticmethod
    def get_document_by_id(document_id):
        """Get a specific document by its ID"""
        try:
            return documents_collection.find_one({"_id": ObjectId(document_id)})
        except:
            return None
    
    @staticmethod
    def update_university(university_code, update_data):
        """Update university information"""
        # Don't allow updating code or x_id through this method
        forbidden_fields = ['code', 'x_id', '_id', 'created_at']
        for field in forbidden_fields:
            update_data.pop(field, None)
        
        if update_data:
            update_data['updated_at'] = datetime.utcnow()
            result = universities_collection.update_one(
                {"code": university_code.lower()},
                {"$set": update_data}
            )
            return result.modified_count > 0
        return False
    
    @staticmethod
    def delete_university(university_code):
        """Delete university and all its documents"""
        # First delete all documents
        documents_collection.delete_many({"university_code": university_code.lower()})
        
        # Then delete the university
        result = universities_collection.delete_one({"code": university_code.lower()})
        return result.deleted_count > 0
    
    @staticmethod
    def delete_document(document_id, university_code):
        """Delete a specific document and update university count"""
        try:
            # Delete the document
            result = documents_collection.delete_one({
                "_id": ObjectId(document_id),
                "university_code": university_code.lower()
            })
            
            if result.deleted_count > 0:
                # Update document count
                universities_collection.update_one(
                    {"code": university_code.lower()},
                    {"$inc": {"document_count": -1}}
                )
                return True
            return False
        except:
            return False
    
    @staticmethod
    def get_university_stats(university_code):
        """Get statistics for a university"""
        university = University.get_university_by_code(university_code)
        if not university:
            return None
        
        # Get document type distribution
        pipeline = [
            {"$match": {"university_code": university_code.lower()}},
            {"$group": {
                "_id": "$document_type",
                "count": {"$sum": 1}
            }}
        ]
        doc_types = list(documents_collection.aggregate(pipeline))
        
        # Get recent documents
        recent_docs = list(documents_collection.find(
            {"university_code": university_code.lower()},
            {"title": 1, "created_at": 1, "document_type": 1}
        ).sort("created_at", -1).limit(5))
        
        return {
            "university": university,
            "total_documents": university.get('document_count', 0),
            "document_types": {doc["_id"]: doc["count"] for doc in doc_types},
            "recent_documents": recent_docs,
            "x_id": university.get('x_id', University.generate_x_id(university_code))
        }
    
    @staticmethod
    def search_universities(query):
        """Search universities by name, code, or description"""
        search_pattern = {"$regex": query, "$options": "i"}
        
        universities = list(universities_collection.find({
            "$or": [
                {"name": search_pattern},
                {"code": search_pattern},
                {"description": search_pattern}
            ]
        }))
        
        # Ensure X-IDs are present
        for uni in universities:
            if 'x_id' not in uni:
                uni['x_id'] = University.generate_x_id(uni.get('code', ''))
        
        return universities
    
    @staticmethod
    def ensure_x_ids_for_existing_universities():
        """
        Utility method to add X-IDs to existing universities that don't have them
        Run this once for database migration
        """
        universities_without_x_id = universities_collection.find({
            "$or": [
                {"x_id": {"$exists": False}},
                {"x_id": None},
                {"x_id": ""}
            ]
        })
        
        updated_count = 0
        for uni in universities_without_x_id:
            x_id = University.generate_x_id(uni.get('code', ''))
            universities_collection.update_one(
                {"_id": uni['_id']},
                {"$set": {"x_id": x_id}}
            )
            updated_count += 1
        
        return updated_count
    
    @staticmethod
    def update_university_metadata(x_id, updated_by_user_id, action, metadata=None):
        """Update university metadata for audit tracking"""
        from datetime import datetime


        update_data = {
            "updated_at": datetime.utcnow(),
            "last_action": {
                "action": action,  # "created", "updated", "document_added", etc.
                "performed_by": updated_by_user_id,
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {}
            }
        }

        # Add to audit trail
        audit_entry = {
            "action": action,
            "performed_by": updated_by_user_id,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {}
        }

        universities_collection.update_one(
            {"x_id": x_id.upper()},
            {
                "$set": update_data,
                "$push": {"audit_trail": audit_entry}
            }
        )
        return True
    
    @staticmethod
    def get_university_by_id(university_id):
        """Get university by MongoDB ObjectId"""
        try:
            # Handle both string and ObjectId inputs
            if isinstance(university_id, str):
                university_id = ObjectId(university_id)
            return universities_collection.find_one({"_id": university_id})
        except Exception as e:
            logging.error(f"Error getting university by ID: {str(e)}")
            return None
        
    @staticmethod
    def update_university_branding(x_id, branding_data):
        """Update university branding information by X-ID"""
        try:
            # Validate branding data structure
            allowed_branding_fields = {
                'branding': {
                    'logo_url', 'favicon_url', 'primary_color', 'secondary_color', 
                    'accent_color', 'custom_css', 'font_family', 'theme_name'
                },
                'domains': {
                    'primary_domain', 'custom_domains', 'subdomain'
                },
                'contact_info': {
                    'website_url', 'support_email', 'phone', 'address'
                }
            }
            
            # Build update document
            update_doc = {
                'updated_at': datetime.utcnow()
            }
            
            # Process branding data
            if 'branding' in branding_data:
                branding = {k: v for k, v in branding_data['branding'].items() 
                           if k in allowed_branding_fields['branding'] and v}
                if branding:
                    update_doc['branding'] = branding
            
            # Process domains data
            if 'domains' in branding_data:
                domains = {k: v for k, v in branding_data['domains'].items() 
                          if k in allowed_branding_fields['domains'] and v}
                if domains:
                    update_doc['domains'] = domains
            
            # Process contact info
            if 'contact_info' in branding_data:
                contact = {k: v for k, v in branding_data['contact_info'].items() 
                          if k in allowed_branding_fields['contact_info'] and v}
                if contact:
                    update_doc['contact_info'] = contact
            
            # Update university
            result = universities_collection.update_one(
                {"x_id": x_id.upper()},
                {"$set": update_doc}
            )
            
            logging.info(f"Updated branding for university {x_id}: {result.modified_count} documents modified")
            return result.modified_count > 0
            
        except Exception as e:
            logging.error(f"Error updating university branding: {str(e)}")
            return False
        
    @staticmethod
    def get_university_branding(x_id):
        """Get university branding information by X-ID"""
        try:
            university = universities_collection.find_one(
                {"x_id": x_id.upper()},
                {
                    "name": 1, "code": 1, "x_id": 1,
                    "branding": 1, "domains": 1, "contact_info": 1
                }
            )
            
            if not university:
                logging.warning(f"University with X-ID {x_id} not found")
                return None
                
            # Ensure branding structure exists with defaults
            university['branding'] = university.get('branding', {
                'logo_url': '',
                'favicon_url': '',
                'primary_color': '#1976d2',
                'secondary_color': '#424242',
                'accent_color': '#ff4081',
                'custom_css': '',
                'font_family': 'Roboto, sans-serif',
                'theme_name': 'default'
            })
            
            university['domains'] = university.get('domains', {
                'primary_domain': '',
                'custom_domains': [],
                'subdomain': ''
            })
            
            university['contact_info'] = university.get('contact_info', {
                'website_url': '',
                'support_email': '',
                'phone': '',
                'address': ''
            })
            
            logging.info(f"Retrieved branding for university {x_id}")
            return university
            
        except Exception as e:
            logging.error(f"Error getting university branding: {str(e)}")
            return None
        
    @staticmethod
    def has_custom_branding(x_id):
        """Check if university has custom branding configured"""
        try:
            university = universities_collection.find_one(
                {"x_id": x_id.upper()},
                {"branding.logo_url": 1, "branding.primary_color": 1, "domains.primary_domain": 1}
            )
            
            if not university:
                logging.warning(f"University with X-ID {x_id} not found")
                return False
                
            branding = university.get('branding', {})
            domains = university.get('domains', {})
            
            # Check if university has custom logo, colors, or domain
            has_custom = bool(
                branding.get('logo_url') or 
                (branding.get('primary_color') and branding.get('primary_color') != '#1976d2') or
                domains.get('primary_domain')
            )
            
            logging.info(f"University {x_id} has custom branding: {has_custom}")
            return has_custom
            
        except Exception as e:
            logging.error(f"Error checking custom branding: {str(e)}")
            return False