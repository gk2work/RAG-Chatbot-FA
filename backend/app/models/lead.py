
from app.models import leads_collection, universities_collection
from bson import ObjectId
from datetime import datetime
import logging

class Lead:

    LEAD_TYPES = {
        'hot': 'Hot Lead',
        'cold': 'Cold Lead', 
        'not_defined': 'Not Defined'
    }

    @staticmethod
    def find_existing_lead(name, email, country, mobile):
        """Find existing lead by name, email, country, and mobile"""
        query = {
            "name": name,
            "email": email,
            "country": country
        }
        
        # Handle mobile field - it could be None or empty string
        if mobile:
            query["mobile"] = mobile
        else:
            query["$or"] = [
                {"mobile": {"$exists": False}},
                {"mobile": None},
                {"mobile": ""}
            ]
        
        return leads_collection.find_one(query)
    
    @staticmethod
    def create_lead(name, email, university_code="csss", country=None, mobile=None, educational_background=None, university_x_id=None):
        """Create a new lead or return existing lead with X-ID support"""
        
        # Check if lead already exists with all matching details
        existing_lead = Lead.find_existing_lead(name, email, country, mobile)
        if existing_lead:
            # Update existing lead timestamp
            leads_collection.update_one(
                {"_id": existing_lead["_id"]},
                {"$set": {"updated_at": datetime.utcnow()}}
            )
            return str(existing_lead["_id"]), True  # Return True to indicate existing lead
        
        # Get university information to resolve X-ID (use passed X-ID if available)
        if not university_x_id:
            university = universities_collection.find_one({"code": university_code.lower()})
            if university:
                university_x_id = university.get('x_id')
                university_name = university.get('name', university_code.upper())
            else:
                university_name = "Unknown University"
        else:
            # If X-ID is provided, get university info by X-ID
            university = universities_collection.find_one({"x_id": university_x_id})
            if university:
                university_name = university.get('name', university_code.upper())
            else:
                university_name = "Unknown University"
        
        # Create new lead with enhanced structure
        lead_data = {
            "name": name,
            "email": email,
            "university_code": university_code.lower(),
            "university_x_id": university_x_id,  # NEW: Store X-ID for admin filtering
            "university_name": university_name,   # NEW: Store name for easy display
            "country": country,
            "mobile": mobile,
            "educational_background": educational_background,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "status": "active",
            "chat_sessions": [],
            "session_summaries": [],
            
            # SOLUTION A: Complete message history storage
            "complete_chat_history": [],  # NEW: Store ALL messages with metadata
            "message_count": 0,           # NEW: Track total messages
            "last_interaction": None,     # NEW: Track last interaction time
            
            # Enhanced analytics
            "engagement_metrics": {
                "total_sessions": 0,
                "total_messages": 0,
                "topics_discussed": [],
                "last_activity": datetime.utcnow()
            }
        }
        
        result = leads_collection.insert_one(lead_data)
        return str(result.inserted_id), False  # Return False to indicate new lead
    
    @staticmethod
    def get_lead_by_id(lead_id):
        """Get a lead by ID"""
        try:
            return leads_collection.find_one({"_id": ObjectId(lead_id)})
        except:
            return None
    
    @staticmethod
    def update_educational_background(lead_id, educational_background):
        """Update educational background for existing lead"""
        try:
            result = leads_collection.update_one(
                {"_id": ObjectId(lead_id)},
                {
                    "$set": {
                        "educational_background": educational_background,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logging.error(f"Error updating educational background for lead {lead_id}: {e}")
            return False
    
    @staticmethod
    def get_lead_by_email(email):
        """Get a lead by email"""
        return leads_collection.find_one({"email": email})
    
    # SOLUTION A: Enhanced message storage - ALL messages saved
    @staticmethod
    def add_complete_message(lead_id, session_id, message_type, content, metadata=None):
        """Add EVERY message to complete chat history - addresses requirement A"""
        try:
            message_entry = {
                "message_id": str(ObjectId()),  # Unique message ID
                "session_id": session_id,
                "message_type": message_type,  # "user" or "assistant"
                "content": content,
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {},
                "university_x_id": metadata.get('university_x_id') if metadata else None
            }
            
            # Extract topics for analytics
            topics = Lead._extract_topics_from_message(content)
            
            result = leads_collection.update_one(
                {"_id": ObjectId(lead_id)},
                {
                    "$push": {"complete_chat_history": message_entry},
                    "$inc": {"message_count": 1},
                    "$set": {
                        "updated_at": datetime.utcnow(),
                        "last_interaction": datetime.utcnow(),
                        "engagement_metrics.last_activity": datetime.utcnow()
                    },
                    "$inc": {"engagement_metrics.total_messages": 1},
                    "$addToSet": {"engagement_metrics.topics_discussed": {"$each": topics}}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logging.error(f"Error adding complete message: {str(e)}")
            return False
    
    @staticmethod
    def _extract_topics_from_message(content):
        """Extract topics from message content for analytics"""
        topics = []
        content_lower = content.lower()
        
        topic_keywords = {
            'admissions': ['admission', 'apply', 'application', 'requirement', 'eligibility'],
            'programs': ['program', 'course', 'degree', 'bachelor', 'master', 'mba', 'curriculum'],
            'fees': ['fee', 'cost', 'tuition', 'price', 'payment', 'scholarship', 'financial'],
            'facilities': ['facility', 'campus', 'library', 'lab', 'infrastructure', 'accommodation'],
            'international': ['visa', 'international', 'foreign', 'study abroad'],
            'career': ['career', 'job', 'placement', 'internship', 'employment']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    # SOLUTION B: Get leads by X-ID for admin filtering
    @staticmethod
    def get_leads_by_university_x_id(university_x_id, limit=50):
        """Get all leads for a specific university X-ID - addresses requirement B"""
        try:
            return list(leads_collection.find(
                {"university_x_id": university_x_id}
            ).sort("updated_at", -1).limit(limit))
        except Exception as e:
            logging.error(f"Error getting leads by X-ID {university_x_id}: {str(e)}")
            return []
    
    @staticmethod
    def get_leads_with_complete_history(university_x_id=None, limit=50):
        """Get leads with their complete message history for admin dashboard"""
        try:
            query = {}
            if university_x_id:
                query["university_x_id"] = university_x_id
            
            leads = list(leads_collection.find(query).sort("updated_at", -1).limit(limit))
            
            # Enhance with message statistics
            for lead in leads:
                complete_history = lead.get('complete_chat_history', [])
                lead['stats'] = {
                    'total_messages': len(complete_history),
                    'user_messages': len([m for m in complete_history if m.get('message_type') == 'user']),
                    'assistant_messages': len([m for m in complete_history if m.get('message_type') == 'assistant']),
                    'last_message_time': complete_history[-1].get('timestamp') if complete_history else None,
                    'engagement_level': Lead._calculate_engagement_level(len(complete_history))
                }
            
            return leads
        except Exception as e:
            logging.error(f"Error getting leads with complete history: {str(e)}")
            return []
    
    @staticmethod
    def _calculate_engagement_level(message_count):
        """Calculate engagement level based on message count"""
        if message_count >= 20:
            return "high"
        elif message_count >= 8:
            return "medium"
        elif message_count >= 2:
            return "low"
        else:
            return "minimal"
    
    @staticmethod
    def add_chat_session(lead_id, session_id):
        """Add a chat session to a lead with enhanced tracking"""
        try:
            result = leads_collection.update_one(
                {"_id": ObjectId(lead_id)},
                {
                    "$push": {"chat_sessions": session_id},
                    "$set": {"updated_at": datetime.utcnow()},
                    "$inc": {"engagement_metrics.total_sessions": 1}
                }
            )
            return result.modified_count > 0
        except:
            return False
    
    @staticmethod
    def add_session_summary(lead_id, session_id, summary):
        """Add a session summary to a lead"""
        try:
            summary_data = {
                "session_id": session_id,
                "summary": summary,
                "created_at": datetime.utcnow()
            }
            result = leads_collection.update_one(
                {"_id": ObjectId(lead_id)},
                {
                    "$push": {"session_summaries": summary_data},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except:
            return False
    
    @staticmethod
    def get_all_leads(limit=50):
        """Get all leads with X-ID information"""
        return list(leads_collection.find().sort("created_at", -1).limit(limit))
    
    @staticmethod
    def update_lead(lead_id, update_data):
        """Update lead information - MISSING METHOD ADDED"""
        try:
            # Add timestamp to update data
            update_data["updated_at"] = datetime.utcnow()
            
            result = leads_collection.update_one(
                {"_id": ObjectId(lead_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logging.info(f"Successfully updated lead {lead_id} with data: {update_data}")
                return True
            else:
                logging.warning(f"No lead found with ID {lead_id} to update")
                return False
                
        except Exception as e:
            logging.error(f"Error updating lead {lead_id}: {str(e)}")
            return False

    @staticmethod
    def update_lead_status(lead_id, status):
        """Update lead status"""
        try:
            result = leads_collection.update_one(
                {"_id": ObjectId(lead_id)},
                {
                    "$set": {
                        "status": status,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except:
            return False
        

    @staticmethod
    def update_lead_categorization(lead_id, lead_type, notes=None):
        """Update lead categorization - NEW METHOD"""
        try:
            if lead_type not in Lead.LEAD_TYPES:
                raise ValueError(f"Invalid lead type: {lead_type}")
            
            update_data = {
                'lead_type': lead_type,
                'updated_at': datetime.utcnow(),
                'categorization_notes': notes,
                'last_interaction': datetime.utcnow()
            }
            
            result = leads_collection.update_one(
                {"_id": ObjectId(lead_id)},
                {"$set": update_data}
            )
            
            logging.info(f"Updated lead {lead_id} categorization to {lead_type}")
            return result.modified_count > 0
            
        except Exception as e:
            logging.error(f"Error updating lead categorization: {str(e)}")
            return False
    
    @staticmethod
    def get_categorization_stats(university_x_id=None):
        """Get lead categorization statistics - NEW METHOD"""
        try:
            # Build query filter
            match_filter = {}
            if university_x_id:
                match_filter["university_x_id"] = university_x_id
            
            pipeline = [
                {"$match": match_filter},
                {
                    "$group": {
                        "_id": "$lead_type",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            results = list(leads_collection.aggregate(pipeline))
            
            # Initialize counts
            stats = {
                'hot': 0,
                'cold': 0,
                'not_defined': 0,
                'total': 0
            }
            
            # Process results
            for result in results:
                lead_type = result.get('_id') or 'not_defined'
                count = result.get('count', 0)
                
                if lead_type in stats:
                    stats[lead_type] = count
                else:
                    # Handle legacy leads without categorization
                    stats['not_defined'] += count
                
                stats['total'] += count
            
            return stats
            
        except Exception as e:
            logging.error(f"Error getting categorization stats: {str(e)}")
            return {'hot': 0, 'cold': 0, 'not_defined': 0, 'total': 0}
    
    @staticmethod
    def get_leads_by_category(university_x_id, lead_type, limit=50):
        """Get leads filtered by category - NEW METHOD"""
        try:
            query = {"university_x_id": university_x_id}
            
            if lead_type and lead_type in Lead.LEAD_TYPES:
                query["lead_type"] = lead_type
            
            return list(leads_collection.find(query)
                       .sort("updated_at", -1)
                       .limit(limit))
            
        except Exception as e:
            logging.error(f"Error getting leads by category: {str(e)}")
            return []
    
    # LEGACY METHOD - Kept for backward compatibility but now stores in complete history too
    @staticmethod
    def add_live_chat_summary(lead_id, session_id, user_message, assistant_response, metadata=None):
        """Legacy method - now also stores in complete chat history"""
        try:
            # Store in complete history (NEW)
            if user_message:
                Lead.add_complete_message(lead_id, session_id, "user", user_message, metadata)
            if assistant_response:
                Lead.add_complete_message(lead_id, session_id, "assistant", assistant_response, metadata)
            
            # Keep legacy format for backward compatibility
            chat_entry = {
                "session_id": session_id,
                "user_message": user_message,
                "assistant_response": assistant_response,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            result = leads_collection.update_one(
                {"_id": ObjectId(lead_id)},
                {
                    "$push": {"live_chat_summaries": chat_entry},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logging.error(f"Error adding live chat summary: {str(e)}")
            return False
    
    @staticmethod
    def get_complete_chat_history(lead_id, session_id=None):
        """Get complete chat history for a lead, optionally filtered by session"""
        try:
            lead = leads_collection.find_one({"_id": ObjectId(lead_id)})
            if not lead:
                return None
            
            complete_history = lead.get("complete_chat_history", [])
            
            if session_id:
                # Filter by specific session
                complete_history = [msg for msg in complete_history if msg.get('session_id') == session_id]
            
            return {
                "lead_id": lead_id,
                "total_messages": len(complete_history),
                "messages": complete_history,
                "engagement_metrics": lead.get("engagement_metrics", {}),
                "university_x_id": lead.get("university_x_id"),
                "university_name": lead.get("university_name")
            }
        except Exception as e:
            logging.error(f"Error getting complete chat history: {str(e)}")
            return None
    
    @staticmethod
    def get_lead_chat_summaries(lead_id):
        """Get all chat summaries for a lead - enhanced with complete history"""
        try:
            lead = leads_collection.find_one({"_id": ObjectId(lead_id)})
            if not lead:
                return None
            
            return {
                "session_summaries": lead.get("session_summaries", []),
                "live_chat_summaries": lead.get("live_chat_summaries", []),
                "complete_chat_history": lead.get("complete_chat_history", []),  # NEW
                "message_count": lead.get("message_count", 0),  # NEW
                "engagement_metrics": lead.get("engagement_metrics", {}),  # NEW
                "university_x_id": lead.get("university_x_id"),  # NEW
                "university_name": lead.get("university_name")   # NEW
            }
        except Exception as e:
            logging.error(f"Error getting lead chat summaries: {str(e)}")
            return None
    
    @staticmethod
    def get_leads_created_today():
        """Get leads created today - for health checks"""
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            return leads_collection.count_documents({"created_at": {"$gte": today_start}})
        except:
            return 0
    
    # SOLUTION B: Admin dashboard methods by X-ID
    @staticmethod
    def get_university_lead_analytics(university_x_id):
        """Get comprehensive analytics for a university by X-ID"""
        try:
            # Get all leads for this university
            leads = Lead.get_leads_by_university_x_id(university_x_id, limit=1000)
            
            if not leads:
                return {
                    "university_x_id": university_x_id,
                    "error": "No leads found for this university"
                }
            
            # Calculate analytics
            total_leads = len(leads)
            total_messages = sum(lead.get('message_count', 0) for lead in leads)
            active_leads = sum(1 for lead in leads if lead.get('status') == 'active')
            
            # Engagement analysis
            engagement_levels = {"high": 0, "medium": 0, "low": 0, "minimal": 0}
            all_topics = []
            
            for lead in leads:
                msg_count = lead.get('message_count', 0)
                level = Lead._calculate_engagement_level(msg_count)
                engagement_levels[level] += 1
                
                # Collect topics
                topics = lead.get('engagement_metrics', {}).get('topics_discussed', [])
                all_topics.extend(topics)
            
            # Topic frequency
            from collections import Counter
            topic_frequency = dict(Counter(all_topics))
            
            return {
                "university_x_id": university_x_id,
                "summary": {
                    "total_leads": total_leads,
                    "active_leads": active_leads,
                    "total_messages": total_messages,
                    "average_messages_per_lead": round(total_messages / total_leads, 2) if total_leads > 0 else 0
                },
                "engagement_distribution": engagement_levels,
                "popular_topics": topic_frequency,
                "last_updated": datetime.utcnow()
            }
            
        except Exception as e:
            logging.error(f"Error getting university analytics: {str(e)}")
            return {"error": str(e)}
        
    