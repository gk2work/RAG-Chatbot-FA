"""
Telegram Bot Routes
Webhook endpoints for receiving and processing Telegram messages
"""

import logging
from flask import Blueprint, request, jsonify
from app.config import Config
from app.integrations.telegram.webhook_handler import TelegramWebhookHandler
from app.integrations.telegram.message_sender import TelegramMessageSender

logger = logging.getLogger(__name__)

telegram_bp = Blueprint('telegram', __name__)

# Initialize Telegram components
webhook_handler = TelegramWebhookHandler()
message_sender = TelegramMessageSender()


@telegram_bp.route('/webhook', methods=['POST'])
def telegram_webhook():
    """
    Main webhook endpoint for Telegram
    Telegram sends updates (messages, button clicks) here
    """
    try:
        # Get update data from Telegram
        update_data = request.get_json()
        
        if not update_data:
            logger.warning("Received empty webhook data")
            return jsonify({'ok': True}), 200
        
        logger.info(f"Received Telegram update: {update_data.get('update_id')}")
        
        # Process the update with webhook handler
        response_data = webhook_handler.process_update(update_data)
        
        if not response_data.get('success'):
            logger.error(f"Handler returned error: {response_data.get('error')}")
            # Still return 200 to Telegram (we handled it)
            return jsonify({'ok': True}), 200
        
        # Send response back to user
        chat_id = response_data.get('chat_id')
        text = response_data.get('text')
        reply_markup = response_data.get('reply_markup')
        parse_mode = response_data.get('parse_mode', 'Markdown')
        
        if chat_id and text:
            # Show "typing..." indicator first (better UX)
            message_sender.send_chat_action(chat_id, "typing")
            
            # Send the actual message
            if len(text) > 4000:
                # Split long messages
                send_result = message_sender.send_long_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            else:
                send_result = message_sender.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            
            logger.info(f"Message sent to chat {chat_id}: {send_result.get('success')}")
        
        # Answer callback query if it's a button click
        callback_query_id = response_data.get('callback_query_id')
        if callback_query_id:
            callback_answer = response_data.get('callback_answer', '✓')
            message_sender.answer_callback_query(
                callback_query_id=callback_query_id,
                text=callback_answer
            )
        
        # Always return 200 OK to Telegram
        return jsonify({'ok': True}), 200
        
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}", exc_info=True)
        # Still return 200 to prevent Telegram from retrying
        return jsonify({'ok': True}), 200


@telegram_bp.route('/webhook', methods=['GET'])
def telegram_webhook_info():
    """
    GET endpoint - shows webhook is configured
    Not used by Telegram, just for verification
    """
    return jsonify({
        'status': 'Telegram webhook endpoint is active',
        'bot_configured': bool(Config.TELEGRAM_BOT_TOKEN),
        'webhook_url': Config.TELEGRAM_WEBHOOK_URL
    }), 200


@telegram_bp.route('/set-webhook', methods=['POST'])
def set_telegram_webhook():
    """
    Set the webhook URL with Telegram
    Call this once after deployment to register your webhook
    
    Usage: POST /api/telegram/set-webhook
    Body: {
        "url": "https://yourdomain.com/api/telegram/webhook"
    }
    """
    try:
        data = request.get_json() or {}
        webhook_url = data.get('url') or Config.TELEGRAM_WEBHOOK_URL
        
        if not webhook_url:
            return jsonify({
                'success': False,
                'error': 'Webhook URL is required'
            }), 400
        
        # Call Telegram API to set webhook
        import requests
        
        api_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/setWebhook"
        payload = {
            'url': webhook_url,
            'allowed_updates': ['message', 'callback_query'],
            'drop_pending_updates': True  # Clear old updates
        }
        
        response = requests.post(api_url, json=payload, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            logger.info(f"Telegram webhook set successfully: {webhook_url}")
            return jsonify({
                'success': True,
                'message': 'Webhook set successfully',
                'webhook_url': webhook_url,
                'telegram_response': result
            }), 200
        else:
            logger.error(f"Failed to set webhook: {result}")
            return jsonify({
                'success': False,
                'error': result.get('description', 'Unknown error'),
                'telegram_response': result
            }), 400
            
    except Exception as e:
        logger.error(f"Error setting webhook: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@telegram_bp.route('/webhook-info', methods=['GET'])
def get_webhook_info():
    """
    Get current webhook information from Telegram
    Useful for debugging
    
    Usage: GET /api/telegram/webhook-info
    """
    try:
        import requests
        
        api_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        
        response = requests.get(api_url, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            webhook_info = result.get('result', {})
            return jsonify({
                'success': True,
                'webhook_info': {
                    'url': webhook_info.get('url'),
                    'has_custom_certificate': webhook_info.get('has_custom_certificate'),
                    'pending_update_count': webhook_info.get('pending_update_count'),
                    'last_error_date': webhook_info.get('last_error_date'),
                    'last_error_message': webhook_info.get('last_error_message'),
                    'max_connections': webhook_info.get('max_connections'),
                    'allowed_updates': webhook_info.get('allowed_updates')
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('description', 'Unknown error')
            }), 400
            
    except Exception as e:
        logger.error(f"Error getting webhook info: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@telegram_bp.route('/delete-webhook', methods=['POST'])
def delete_telegram_webhook():
    """
    Delete the webhook (useful for switching to polling or debugging)
    
    Usage: POST /api/telegram/delete-webhook
    """
    try:
        import requests
        
        api_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/deleteWebhook"
        payload = {
            'drop_pending_updates': True
        }
        
        response = requests.post(api_url, json=payload, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            logger.info("Telegram webhook deleted successfully")
            return jsonify({
                'success': True,
                'message': 'Webhook deleted successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('description', 'Unknown error')
            }), 400
            
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@telegram_bp.route('/test-message', methods=['POST'])
def send_test_message():
    """
    Test endpoint - send a test message to a chat
    Useful for debugging
    
    Usage: POST /api/telegram/test-message
    Body: {
        "chat_id": 123456789,
        "text": "Hello from bot!"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'chat_id' not in data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'chat_id and text are required'
            }), 400
        
        chat_id = data['chat_id']
        text = data['text']
        reply_markup = data.get('reply_markup')
        
        result = message_sender.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup
        )
        
        return jsonify(result), 200 if result.get('success') else 400
        
    except Exception as e:
        logger.error(f"Error sending test message: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@telegram_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    
    Usage: GET /api/telegram/health
    """
    try:
        # Check if bot token is configured
        bot_configured = bool(Config.TELEGRAM_BOT_TOKEN)
        
        # Try to get bot info from Telegram
        bot_info = None
        if bot_configured:
            import requests
            api_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/getMe"
            try:
                response = requests.get(api_url, timeout=5)
                result = response.json()
                if result.get('ok'):
                    bot_info = result.get('result')
            except:
                pass
        
        return jsonify({
            'status': 'healthy',
            'bot_configured': bot_configured,
            'bot_info': bot_info,
            'webhook_handler_ready': webhook_handler is not None,
            'message_sender_ready': message_sender is not None
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
