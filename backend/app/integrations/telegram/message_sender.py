"""
Telegram Message Sender
Sends messages, buttons, and media to Telegram users
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from app.config import Config

logger = logging.getLogger(__name__)


class TelegramMessageSender:
    """Send messages to Telegram users via Bot API"""
    
    def __init__(self):
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        if not self.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not configured!")
            raise ValueError("Telegram bot token is required")
    
    def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[Dict] = None,
        parse_mode: str = "Markdown",
        disable_web_page_preview: bool = True
    ) -> Dict[str, Any]:
        """
        Send a text message to a Telegram chat
        
        Args:
            chat_id: Telegram chat ID
            text: Message text (max 4096 characters)
            reply_markup: Inline keyboard buttons (optional)
            parse_mode: "Markdown" or "HTML"
            disable_web_page_preview: Don't show link previews
            
        Returns:
            Dict with response from Telegram API
        """
        try:
            url = f"{self.base_url}/sendMessage"
            
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": disable_web_page_preview
            }
            
            if reply_markup:
                payload["reply_markup"] = reply_markup
            
            logger.info(f"Sending message to chat {chat_id}: {text[:50]}...")
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"Message sent successfully to chat {chat_id}")
                return {
                    'success': True,
                    'message_id': result['result']['message_id']
                }
            else:
                logger.error(f"Telegram API error: {result}")
                return {
                    'success': False,
                    'error': result.get('description', 'Unknown error')
                }
                
        except requests.exceptions.Timeout:
            logger.error("Telegram API timeout")
            return {
                'success': False,
                'error': 'Request timeout'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending message to Telegram: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_long_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[Dict] = None,
        parse_mode: str = "Markdown"
    ) -> List[Dict[str, Any]]:
        """
        Send long message (split if > 4096 chars)
        
        Returns:
            List of response dicts for each message chunk
        """
        max_length = 4000  # Leave some buffer
        
        if len(text) <= max_length:
            return [self.send_message(chat_id, text, reply_markup, parse_mode)]
        
        # Split into chunks
        chunks = []
        current_chunk = ""
        
        for paragraph in text.split('\n\n'):
            if len(current_chunk) + len(paragraph) + 2 <= max_length:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Send all chunks
        results = []
        for i, chunk in enumerate(chunks):
            # Only add buttons to last message
            markup = reply_markup if i == len(chunks) - 1 else None
            result = self.send_message(chat_id, chunk, markup, parse_mode)
            results.append(result)
        
        return results
    
    def answer_callback_query(
        self,
        callback_query_id: str,
        text: str = "✓",
        show_alert: bool = False
    ) -> Dict[str, Any]:
        """
        Answer a callback query (acknowledge button click)
        
        Args:
            callback_query_id: ID from callback query
            text: Text to show (optional)
            show_alert: Show as alert popup vs toast notification
            
        Returns:
            Dict with success status
        """
        try:
            url = f"{self.base_url}/answerCallbackQuery"
            
            payload = {
                "callback_query_id": callback_query_id,
                "text": text,
                "show_alert": show_alert
            }
            
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                'success': result.get('ok', False)
            }
            
        except Exception as e:
            logger.error(f"Error answering callback query: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_chat_action(
        self,
        chat_id: int,
        action: str = "typing"
    ) -> Dict[str, Any]:
        """
        Send chat action (e.g., "typing..." indicator)
        
        Args:
            chat_id: Telegram chat ID
            action: "typing", "upload_photo", "upload_document", etc.
            
        Returns:
            Dict with success status
        """
        try:
            url = f"{self.base_url}/sendChatAction"
            
            payload = {
                "chat_id": chat_id,
                "action": action
            }
            
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                'success': result.get('ok', False)
            }
            
        except Exception as e:
            logger.error(f"Error sending chat action: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: Optional[Dict] = None,
        parse_mode: str = "Markdown"
    ) -> Dict[str, Any]:
        """
        Edit an existing message (useful for updating button responses)
        
        Args:
            chat_id: Telegram chat ID
            message_id: ID of message to edit
            text: New message text
            reply_markup: New buttons (optional)
            parse_mode: "Markdown" or "HTML"
            
        Returns:
            Dict with success status
        """
        try:
            url = f"{self.base_url}/editMessageText"
            
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            if reply_markup:
                payload["reply_markup"] = reply_markup
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                'success': result.get('ok', False)
            }
            
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_document(
        self,
        chat_id: int,
        document_url: str,
        caption: Optional[str] = None,
        reply_markup: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Send a document/file to user
        
        Args:
            chat_id: Telegram chat ID
            document_url: URL or file_id of document
            caption: Optional caption text
            reply_markup: Optional buttons
            
        Returns:
            Dict with success status
        """
        try:
            url = f"{self.base_url}/sendDocument"
            
            payload = {
                "chat_id": chat_id,
                "document": document_url
            }
            
            if caption:
                payload["caption"] = caption
            
            if reply_markup:
                payload["reply_markup"] = reply_markup
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                'success': result.get('ok', False),
                'message_id': result.get('result', {}).get('message_id')
            }
            
        except Exception as e:
            logger.error(f"Error sending document: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_photo(
        self,
        chat_id: int,
        photo_url: str,
        caption: Optional[str] = None,
        reply_markup: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Send a photo to user
        
        Args:
            chat_id: Telegram chat ID
            photo_url: URL or file_id of photo
            caption: Optional caption text
            reply_markup: Optional buttons
            
        Returns:
            Dict with success status
        """
        try:
            url = f"{self.base_url}/sendPhoto"
            
            payload = {
                "chat_id": chat_id,
                "photo": photo_url
            }
            
            if caption:
                payload["caption"] = caption
            
            if reply_markup:
                payload["reply_markup"] = reply_markup
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                'success': result.get('ok', False),
                'message_id': result.get('result', {}).get('message_id')
            }
            
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return {
                'success': False,
                'error': str(e)
            }