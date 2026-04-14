"""
Message formatter for different platforms
Handles markdown, emojis, and platform-specific formatting
"""

import re
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class MessageFormatter:
    """Format messages for different platforms"""
    
    # Emoji mappings for consistency
    EMOJIS = {
        'wave': '👋',
        'graduation': '🎓',
        'book': '📚',
        'phone': '📞',
        'email': '📧',
        'location': '📍',
        'check': '✅',
        'cross': '❌',
        'info': 'ℹ️',
        'warning': '⚠️',
        'money': '💰',
        'calendar': '📅',
        'clock': '🕐',
        'rocket': '🚀',
        'star': '⭐',
        'question': '❓'
    }
    
    @staticmethod
    def format_for_telegram(text: str, parse_mode: str = 'Markdown') -> Dict[str, Any]:
        """
        Format message for Telegram
        Telegram supports MarkdownV2, Markdown, and HTML
        
        Args:
            text: Message text
            parse_mode: 'Markdown', 'MarkdownV2', or 'HTML'
        
        Returns:
            Dict with 'text' and 'parse_mode'
        """
        # Telegram supports rich formatting natively
        # Clean up excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return {
            'text': text,
            'parse_mode': parse_mode
        }
    
    @staticmethod
    def format_for_whatsapp(text: str) -> str:
        """
        Format message for WhatsApp
        WhatsApp API sends plain text (no markdown in API)
        But we can use Unicode formatting for better readability
        
        WhatsApp app supports (user-facing):
        - *bold* 
        - _italic_
        - ~strikethrough~
        - ```monospace```
        
        But API sends plain text, so we focus on:
        - Clean formatting
        - Emojis for visual appeal
        - Proper line breaks
        """
        
        # Clean up markdown symbols that won't render in WhatsApp API
        # Remove code blocks (```)
        text = re.sub(r'```[\s\S]*?```', lambda m: m.group(0).replace('```', ''), text)
        
        # Clean up excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Replace markdown headers with emoji-enhanced headers
        # ## Header -> 📌 HEADER
        text = re.sub(r'^##\s+(.+)$', lambda m: f"📌 {m.group(1).upper()}", text, flags=re.MULTILINE)
        text = re.sub(r'^#\s+(.+)$', lambda m: f"🎯 {m.group(1).upper()}", text, flags=re.MULTILINE)
        
        # Enhance bullet points with emojis
        text = re.sub(r'^\*\s+', '• ', text, flags=re.MULTILINE)
        text = re.sub(r'^-\s+', '• ', text, flags=re.MULTILINE)
        
        # Format links nicely: [text](url) -> text: url
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'\1: \2', text)
        
        return text.strip()
    
    @staticmethod
    def truncate_message(text: str, max_length: int = 4000, platform: str = 'telegram') -> List[str]:
        """
        Split long messages into chunks
        Telegram: 4096 char limit (using 4000 for safety)
        WhatsApp: 4096 char limit (using 4000 for safety)
        
        Args:
            text: Message text
            max_length: Maximum length per chunk
            platform: 'telegram' or 'whatsapp'
        
        Returns:
            List of message chunks
        """
        if len(text) <= max_length:
            return [text]
        
        # Split by paragraphs first (preserves formatting)
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            # If single paragraph is too long, split by sentences
            if len(para) > max_length:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 2 <= max_length:
                        current_chunk += sentence + " "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + " "
            else:
                # Normal paragraph handling
                if len(current_chunk) + len(para) + 2 <= max_length:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Add continuation indicators for multi-part messages
        if len(chunks) > 1:
            for i in range(len(chunks)):
                if i < len(chunks) - 1:
                    chunks[i] += f"\n\n_(Continued... {i+1}/{len(chunks)})_"
                else:
                    chunks[i] = f"_(Continued {i+1}/{len(chunks)})_\n\n" + chunks[i]
        
        return chunks
    
    @staticmethod
    def extract_buttons_from_text(text: str) -> Tuple[str, List[str]]:
        """
        Extract button options from RAG response
        Look for patterns like [Button: text] or numbered lists
        
        Args:
            text: Message text
        
        Returns:
            Tuple of (cleaned_text, button_options)
        """
        buttons = []
        
        # Pattern 1: [Button: Text] or [Button:Text]
        button_pattern = r'\[Button:\s*([^\]]+)\]'
        matches = re.findall(button_pattern, text, re.IGNORECASE)
        buttons.extend([m.strip() for m in matches])
        text = re.sub(button_pattern, '', text, flags=re.IGNORECASE)
        
        # Pattern 2: Numbered list at end (only if 2+ consecutive items)
        # 1. Option One
        # 2. Option Two
        lines = text.split('\n')
        numbered_options = []
        consecutive_count = 0
        
        for line in lines:
            match = re.match(r'^\d+\.\s+(.+)$', line.strip())
            if match:
                numbered_options.append(match.group(1).strip())
                consecutive_count += 1
            else:
                # Reset if pattern breaks
                if consecutive_count > 0 and consecutive_count < 2:
                    numbered_options = []
                consecutive_count = 0
        
        # Only use numbered list if we found 2+ options
        if len(numbered_options) >= 2:
            buttons.extend(numbered_options)
            # Remove numbered list from text
            text = '\n'.join([
                l for l in lines 
                if not re.match(r'^\d+\.\s+', l.strip())
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_buttons = []
        for btn in buttons:
            if btn.lower() not in seen:
                seen.add(btn.lower())
                unique_buttons.append(btn)
        
        return text.strip(), unique_buttons[:10]  # Max 10 buttons
    
    @staticmethod
    def add_emoji(text: str, emoji_name: str, position: str = 'start') -> str:
        """
        Add emoji to text
        
        Args:
            text: Message text
            emoji_name: Emoji name from EMOJIS dict
            position: 'start' or 'end'
        
        Returns:
            Text with emoji
        """
        emoji = MessageFormatter.EMOJIS.get(emoji_name, '')
        if not emoji:
            return text
        
        if position == 'start':
            return f"{emoji} {text}"
        else:
            return f"{text} {emoji}"
    
    @staticmethod
    def format_welcome_message(platform: str, university_name: str, user_name: str = None) -> str:
        """
        Create platform-specific welcome message
        
        Args:
            platform: 'telegram' or 'whatsapp'
            university_name: Name of the university
            user_name: User's name (optional)
        
        Returns:
            Formatted welcome message
        """
        greeting = f"Hello {user_name}!" if user_name else "Hello!"
        
        message = f"""👋 {greeting}

Welcome to **{university_name}** Admission Assistant!

I'm here to help you with:
- Program information 📚
- Admission requirements ✅
- Fees and scholarships 💰
- Application process 📝
- Campus facilities 🏫

Just ask me anything, and I'll be happy to help!

_Type your question or choose from suggested options._"""
        
        if platform == 'whatsapp':
            return MessageFormatter.format_for_whatsapp(message)
        else:
            return message
    
    @staticmethod
    def format_error_message(platform: str, error_type: str = 'general') -> str:
        """
        Create platform-specific error message
        
        Args:
            platform: 'telegram' or 'whatsapp'
            error_type: 'general', 'network', 'not_found'
        
        Returns:
            Formatted error message
        """
        messages = {
            'general': "⚠️ Sorry, I encountered an error. Please try again.",
            'network': "⚠️ Network error. Please check your connection and try again.",
            'not_found': "❌ Sorry, I couldn't find information about that. Please rephrase your question."
        }
        
        message = messages.get(error_type, messages['general'])
        
        if platform == 'whatsapp':
            return MessageFormatter.format_for_whatsapp(message)
        else:
            return message
    
    @staticmethod
    def clean_text_for_display(text: str) -> str:
        """
        Clean text for better display (remove extra spaces, normalize)
        
        Args:
            text: Raw text
        
        Returns:
            Cleaned text
        """
        # Remove extra spaces
        text = re.sub(r' +', ' ', text)
        
        # Remove spaces before punctuation
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)
        
        # Normalize newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()