"""
WhatsApp Webhook Handler
Processes incoming messages from Meta's WhatsApp Business API
"""

import logging
import hmac
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WhatsAppWebhookHandler:
    """Handle WhatsApp webhook events"""
    
    @staticmethod
    def verify_webhook(mode: str, token: str, verify_token: str) -> Optional[str]:
        """
        Verify webhook subscription from Meta
        This is called when you set up the webhook in Meta dashboard
        
        Args:
            mode: Should be 'subscribe'
            token: Token sent by Meta
            verify_token: Your verify token from .env
        
        Returns:
            Challenge string if verified, None otherwise
        """
        if mode == "subscribe" and token == verify_token:
            logger.info("Webhook verified successfully")
            return True
        else:
            logger.warning(f"Webhook verification failed. Mode: {mode}")
            return False
    
    @staticmethod
    def verify_signature(payload: bytes, signature: str, app_secret: str) -> bool:
        """
        Verify that webhook request came from Meta (optional but recommended)
        
        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value
            app_secret: Your app secret from Meta dashboard
        
        Returns:
            True if signature is valid
        """
        if not signature:
            return True  # Skip if no signature provided
        
        try:
            # Remove 'sha256=' prefix
            expected_signature = signature.split('sha256=')[-1]
            
            # Calculate HMAC
            mac = hmac.new(
                app_secret.encode('utf-8'),
                msg=payload,
                digestmod=hashlib.sha256
            )
            
            return hmac.compare_digest(mac.hexdigest(), expected_signature)
        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False
    
    @staticmethod
    def parse_webhook_payload(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse incoming webhook payload from WhatsApp
        
        Meta sends webhooks in this format:
        {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15551234567",
                            "phone_number_id": "123456789"
                        },
                        "contacts": [{
                            "profile": {"name": "John Doe"},
                            "wa_id": "919876543210"
                        }],
                        "messages": [{
                            "from": "919876543210",
                            "id": "wamid.XXX",
                            "timestamp": "1234567890",
                            "type": "text",
                            "text": {"body": "Hello"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        Args:
            payload: Webhook payload from Meta
        
        Returns:
            Parsed message data or None if not a message event
        """
        try:
            # Check if this is a WhatsApp Business Account webhook
            if payload.get("object") != "whatsapp_business_account":
                logger.warning(f"Unknown webhook object: {payload.get('object')}")
                return None
            
            # Get first entry
            entry = payload.get("entry", [])
            if not entry:
                logger.warning("No entry in webhook payload")
                return None
            
            # Get first change
            changes = entry[0].get("changes", [])
            if not changes:
                logger.warning("No changes in webhook entry")
                return None
            
            change = changes[0]
            value = change.get("value", {})
            
            # Check if this is a message event
            if change.get("field") != "messages":
                logger.info(f"Ignoring non-message event: {change.get('field')}")
                return None
            
            # Get messages
            messages = value.get("messages", [])
            if not messages:
                # Could be a status update, ignore
                logger.info("No messages in webhook (probably status update)")
                return None
            
            message = messages[0]
            
            # Get contact info
            contacts = value.get("contacts", [])
            contact_name = "User"
            if contacts:
                contact_name = contacts[0].get("profile", {}).get("name", "User")
            
            # Get metadata
            metadata = value.get("metadata", {})
            
            # Parse message based on type
            message_type = message.get("type")
            message_content = ""
            
            if message_type == "text":
                message_content = message.get("text", {}).get("body", "")
            elif message_type == "button":
                message_content = message.get("button", {}).get("text", "")
            elif message_type == "interactive":
                interactive = message.get("interactive", {})
                if interactive.get("type") == "button_reply":
                    message_content = interactive.get("button_reply", {}).get("title", "")
                elif interactive.get("type") == "list_reply":
                    message_content = interactive.get("list_reply", {}).get("title", "")
            else:
                logger.warning(f"Unsupported message type: {message_type}")
                return None
            
            # Return parsed data
            return {
                "message_id": message.get("id"),
                "from_number": message.get("from"),  # User's WhatsApp number
                "phone_number_id": metadata.get("phone_number_id"),  # Your business number ID
                "contact_name": contact_name,
                "message_type": message_type,
                "message_content": message_content,
                "timestamp": int(message.get("timestamp", 0)),
                "raw_message": message  # Keep raw for debugging
            }
            
        except Exception as e:
            logger.error(f"Error parsing webhook payload: {e}", exc_info=True)
            return None
    
    @staticmethod
    def should_process_message(message_data: Dict[str, Any]) -> bool:
        """
        Determine if we should process this message
        (Skip if it's from us, or too old, etc.)
        
        Args:
            message_data: Parsed message data
        
        Returns:
            True if we should process the message
        """
        # Skip if no message content
        if not message_data.get("message_content"):
            logger.info("Skipping message with no content")
            return False
        
        # Skip if message is too old (older than 5 minutes)
        message_timestamp = message_data.get("timestamp", 0)
        current_timestamp = int(datetime.utcnow().timestamp())
        
        if current_timestamp - message_timestamp > 300:  # 5 minutes
            logger.info(f"Skipping old message (age: {current_timestamp - message_timestamp}s)")
            return False
        
        return True
    
    @staticmethod
    def extract_user_info(message_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract user information for session creation
        
        Args:
            message_data: Parsed message data
        
        Returns:
            User info dict
        """
        # WhatsApp number format: 919876543210 (without +)
        phone_number = message_data.get("from_number", "")
        
        # Add + prefix if not present
        if phone_number and not phone_number.startswith("+"):
            phone_number = f"+{phone_number}"
        
        return {
            "platform": "whatsapp",
            "user_identifier": phone_number,
            "name": message_data.get("contact_name", "WhatsApp User"),
            "phone": phone_number,
            "metadata": {
                "phone_number_id": message_data.get("phone_number_id"),
                "message_id": message_data.get("message_id")
            }
        }
    
    @staticmethod
    def is_duplicate_message(message_id: str, cache_store: Dict = None) -> bool:
        """
        Check if we've already processed this message
        (WhatsApp sometimes sends duplicate webhooks)
        
        Args:
            message_id: WhatsApp message ID
            cache_store: Optional cache dict (use Redis in production)
        
        Returns:
            True if duplicate
        """
        # Simple in-memory check (use Redis in production)
        if cache_store is None:
            # In production, use Redis with TTL
            # For now, we'll skip duplicate checking
            return False
        
        if message_id in cache_store:
            return True
        
        # Mark as processed
        cache_store[message_id] = datetime.utcnow()
        
        return False
    
    @staticmethod
    def format_error_response(error_type: str = "general") -> str:
        """
        Get error message to send to user
        
        Args:
            error_type: Type of error
        
        Returns:
            Error message
        """
        errors = {
            "general": "⚠️ Sorry, I encountered an error. Please try again in a moment.",
            "rate_limit": "⏳ You're sending messages too quickly. Please wait a moment.",
            "unsupported": "📎 Sorry, I can only process text messages at the moment.",
            "processing": "⚙️ Processing your request... Please wait."
        }
        
        return errors.get(error_type, errors["general"])