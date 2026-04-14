"""
WhatsApp Message Sender
Sends messages to users via Meta's WhatsApp Business API
"""

import logging
import aiohttp
import asyncio
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class WhatsAppMessageSender:
    """Send messages via WhatsApp Business API"""
    
    def __init__(self, access_token: str, phone_number_id: str, api_version: str = "v21.0"):
        """
        Initialize WhatsApp sender
        
        Args:
            access_token: WhatsApp API access token
            phone_number_id: Your WhatsApp Business phone number ID
            api_version: Meta API version (default: v21.0)
        """
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_version = api_version
        self.base_url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    
    async def send_text_message(
        self, 
        to_number: str, 
        message: str,
        preview_url: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Send a text message
        
        Args:
            to_number: Recipient's WhatsApp number (with country code, no +)
            message: Message text (max 4096 characters)
            preview_url: Enable URL preview
        
        Returns:
            API response or None if failed
        """
        # Remove + from phone number if present
        to_number = to_number.replace("+", "")
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": message
            }
        }
        
        return await self._send_request(payload)
    
    async def send_text_with_buttons(
        self,
        to_number: str,
        message: str,
        buttons: List[str],
        header: Optional[str] = None,
        footer: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send message with quick reply buttons (max 3 buttons)
        
        Args:
            to_number: Recipient's WhatsApp number
            message: Message body text
            buttons: List of button texts (max 3, max 20 chars each)
            header: Optional header text
            footer: Optional footer text
        
        Returns:
            API response or None if failed
        """
        # Remove + from phone number
        to_number = to_number.replace("+", "")
        
        # WhatsApp allows max 3 buttons
        buttons = buttons[:3]
        
        # Create button objects
        button_objects = []
        for idx, button_text in enumerate(buttons):
            # Truncate to 20 characters (WhatsApp limit)
            button_text = button_text[:20]
            button_objects.append({
                "type": "reply",
                "reply": {
                    "id": f"btn_{idx}",
                    "title": button_text
                }
            })
        
        # Build interactive message
        interactive_body = {
            "type": "button",
            "body": {
                "text": message
            },
            "action": {
                "buttons": button_objects
            }
        }
        
        # Add optional header
        if header:
            interactive_body["header"] = {
                "type": "text",
                "text": header[:60]  # Max 60 chars
            }
        
        # Add optional footer
        if footer:
            interactive_body["footer"] = {
                "text": footer[:60]  # Max 60 chars
            }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "interactive",
            "interactive": interactive_body
        }
        
        return await self._send_request(payload)
    
    async def send_list_message(
        self,
        to_number: str,
        message: str,
        button_text: str,
        sections: List[Dict[str, Any]],
        header: Optional[str] = None,
        footer: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send message with list menu (for more than 3 options)
        
        Args:
            to_number: Recipient's WhatsApp number
            message: Message body text
            button_text: Text for the list button (e.g., "View Options")
            sections: List of sections, each with rows
                Example: [
                    {
                        "title": "Programs",
                        "rows": [
                            {"id": "pg_1", "title": "Computer Science", "description": "4-year program"},
                            {"id": "pg_2", "title": "Business Admin", "description": "3-year program"}
                        ]
                    }
                ]
            header: Optional header text
            footer: Optional footer text
        
        Returns:
            API response or None if failed
        """
        # Remove + from phone number
        to_number = to_number.replace("+", "")
        
        # Build interactive message
        interactive_body = {
            "type": "list",
            "body": {
                "text": message
            },
            "action": {
                "button": button_text[:20],  # Max 20 chars
                "sections": sections[:10]  # Max 10 sections
            }
        }
        
        # Add optional header
        if header:
            interactive_body["header"] = {
                "type": "text",
                "text": header[:60]
            }
        
        # Add optional footer
        if footer:
            interactive_body["footer"] = {
                "text": footer[:60]
            }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "interactive",
            "interactive": interactive_body
        }
        
        return await self._send_request(payload)
    
    async def send_template_message(
        self,
        to_number: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[List[Dict]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send a pre-approved template message
        (Used for initiating conversations outside 24-hour window)
        
        Args:
            to_number: Recipient's WhatsApp number
            template_name: Name of approved template
            language_code: Language code (default: en)
            components: Template parameters
        
        Returns:
            API response or None if failed
        """
        # Remove + from phone number
        to_number = to_number.replace("+", "")
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        if components:
            payload["template"]["components"] = components
        
        return await self._send_request(payload)
    
    async def mark_as_read(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Mark a message as read
        
        Args:
            message_id: WhatsApp message ID
        
        Returns:
            API response or None if failed
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        return await self._send_request(payload)
    
    async def send_reaction(
        self,
        to_number: str,
        message_id: str,
        emoji: str
    ) -> Optional[Dict[str, Any]]:
        """
        React to a message with an emoji
        
        Args:
            to_number: Recipient's WhatsApp number
            message_id: Message ID to react to
            emoji: Emoji to react with (e.g., "👍")
        
        Returns:
            API response or None if failed
        """
        # Remove + from phone number
        to_number = to_number.replace("+", "")
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "reaction",
            "reaction": {
                "message_id": message_id,
                "emoji": emoji
            }
        }
        
        return await self._send_request(payload)
    
    async def _send_request(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Internal method to send API request
        
        Args:
            payload: Request payload
        
        Returns:
            API response or None if failed
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        logger.info(f"Message sent successfully: {response_data.get('messages', [{}])[0].get('id')}")
                        return response_data
                    else:
                        logger.error(f"WhatsApp API error: {response.status} - {response_data}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("WhatsApp API request timeout")
            return None
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}", exc_info=True)
            return None
    
    async def send_typing_indicator(self, to_number: str, duration: int = 3):
        """
        Show typing indicator (simulate typing)
        Note: WhatsApp doesn't have official typing API, 
        this is a placeholder for future implementation
        
        Args:
            to_number: Recipient's WhatsApp number
            duration: How long to "type" (seconds)
        """
        # WhatsApp doesn't support typing indicators via API yet
        # But we can add a small delay to simulate thinking time
        await asyncio.sleep(min(duration, 3))
    
    def create_button_list_from_options(
        self,
        options: List[str],
        max_buttons: int = 3
    ) -> tuple:
        """
        Helper to decide between buttons (≤3 options) or list (>3 options)
        
        Args:
            options: List of option texts
            max_buttons: Maximum buttons before switching to list
        
        Returns:
            Tuple of (use_buttons: bool, formatted_options)
        """
        if len(options) <= max_buttons:
            # Use buttons
            return True, options[:3]
        else:
            # Use list menu - format as sections
            rows = [
                {
                    "id": f"opt_{idx}",
                    "title": opt[:24],  # Max 24 chars for list title
                    "description": opt[24:72] if len(opt) > 24 else ""  # Optional description
                }
                for idx, opt in enumerate(options[:10])  # Max 10 items
            ]
            
            sections = [{
                "title": "Options",
                "rows": rows
            }]
            
            return False, sections