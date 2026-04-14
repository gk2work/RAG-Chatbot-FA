"""
WhatsApp Routes
Flask endpoints for WhatsApp webhook
"""

import logging
from flask import Blueprint, request, jsonify
from app.config import Config
from app.integrations.whatsapp.webhook_handler import WhatsAppWebhookHandler
from app.integrations.whatsapp.message_sender import WhatsAppMessageSender
from app.integrations.common.session_manager import BotSessionManager
from app.integrations.common.message_formatter import MessageFormatter
import asyncio

logger = logging.getLogger(__name__)

# Create Blueprint
whatsapp_bp = Blueprint('whatsapp', __name__, url_prefix='/api/whatsapp')

# Initialize components
webhook_handler = WhatsAppWebhookHandler()
message_formatter = MessageFormatter()

# Message cache to prevent duplicates (use Redis in production)
processed_messages = {}


@whatsapp_bp.route('/webhook', methods=['GET'])
def verify_webhook():
    """
    Webhook verification endpoint
    Meta calls this when you first set up the webhook
    
    Expected query params:
    - hub.mode=subscribe
    - hub.verify_token=YOUR_VERIFY_TOKEN
    - hub.challenge=CHALLENGE_STRING
    """
    try:
        # Get query parameters
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

         # 🔍 DEBUG: Log what we're comparing
        logger.info(f"Webhook verification request - Mode: {mode}")
        logger.info(f"🔍 DEBUG - Received token: '{token}'")
        logger.info(f"🔍 DEBUG - Expected token: '{Config.WHATSAPP_VERIFY_TOKEN}'")
        logger.info(f"🔍 DEBUG - Tokens match: {token == Config.WHATSAPP_VERIFY_TOKEN}")
        
        logger.info(f"Webhook verification request - Mode: {mode}")
        
        # Verify the token
        if webhook_handler.verify_webhook(mode, token, Config.WHATSAPP_VERIFY_TOKEN):
            logger.info("Webhook verified successfully!")
            # Return challenge to complete verification
            return challenge, 200
        else:
            logger.warning("Webhook verification failed - invalid token")
            return jsonify({"error": "Verification failed"}), 403
            
    except Exception as e:
        logger.error(f"Error in webhook verification: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@whatsapp_bp.route('/webhook', methods=['POST'])
def handle_webhook():
    """
    Main webhook endpoint for incoming WhatsApp messages
    Meta sends POST requests here when users send messages
    """
    try:
        # Get raw payload
        payload = request.get_json()
        
        if not payload:
            logger.warning("Received empty webhook payload")
            return jsonify({"status": "ok"}), 200
        
        logger.info(f"Received webhook: {payload}")
        
        # Optional: Verify signature (recommended for production)
        # signature = request.headers.get('X-Hub-Signature-256', '')
        # if not webhook_handler.verify_signature(request.data, signature, Config.WHATSAPP_APP_SECRET):
        #     logger.warning("Invalid webhook signature")
        #     return jsonify({"error": "Invalid signature"}), 403
        
        # Parse the webhook payload
        message_data = webhook_handler.parse_webhook_payload(payload)
        
        if not message_data:
            # Not a message event (could be status update)
            logger.info("Webhook received but no message to process")
            return jsonify({"status": "ok"}), 200
        
        # Check if we should process this message
        if not webhook_handler.should_process_message(message_data):
            logger.info("Message filtered out (too old or invalid)")
            return jsonify({"status": "ok"}), 200
        
        # Check for duplicate
        message_id = message_data.get("message_id")
        if webhook_handler.is_duplicate_message(message_id, processed_messages):
            logger.info(f"Duplicate message ignored: {message_id}")
            return jsonify({"status": "ok"}), 200
        
        # Process message asynchronously
        asyncio.run(process_whatsapp_message(message_data))
        
        # Return 200 immediately (Meta requires quick response)
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Error handling webhook: {e}", exc_info=True)
        # Still return 200 to prevent Meta from retrying
        return jsonify({"status": "error", "message": str(e)}), 200


async def process_whatsapp_message(message_data: dict):
    """
    Process incoming WhatsApp message asynchronously
    
    Args:
        message_data: Parsed message data from webhook
    """
    sender = None
    
    try:
        # Import here to avoid circular imports
        from app.models.chat import ChatSession
        from app.models import get_db
        
        # Extract user info
        user_info = webhook_handler.extract_user_info(message_data)
        from_number = user_info["user_identifier"]
        message_content = message_data["message_content"]
        
        logger.info(f"Processing message from {from_number}: {message_content}")
        
        # Initialize message sender
        sender = WhatsAppMessageSender(
            access_token=Config.WHATSAPP_ACCESS_TOKEN,
            phone_number_id=Config.WHATSAPP_PHONE_NUMBER_ID
        )
        
        # Mark message as read (optional but good UX)
        await sender.mark_as_read(message_data["message_id"])
        
        # Show typing indicator (simulate thinking)
        await sender.send_typing_indicator(from_number, duration=2)
        
        # Get or create session
        session_id, is_new_session = BotSessionManager.get_or_create_session(
            platform='whatsapp',
            user_identifier=from_number,
            university_x_id=Config.DEFAULT_UNIVERSITY_X_ID,
            user_metadata=user_info.get("metadata")
        )
        
        logger.info(f"Session: {session_id} (new: {is_new_session})")
        
        # If new session, send welcome message
        if is_new_session:
            # Get university info for welcome message
            db = get_db()
            university = db['universities'].find_one({'x_id': Config.DEFAULT_UNIVERSITY_X_ID})
            university_name = university.get('name', 'Our University') if university else 'Our University'
            
            welcome_msg = message_formatter.format_welcome_message(
                platform='whatsapp',
                university_name=university_name,
                user_name=user_info.get("name")
            )
            
            await sender.send_text_message(from_number, welcome_msg)
            await asyncio.sleep(1)  # Small delay before processing their message
        
        # Add user message to session
        BotSessionManager.add_message_to_session(
            session_id=session_id,
            role='user',
            content=message_content
        )
        
        # Get session for context
        session = BotSessionManager.get_session(session_id)
        
        # Get RAG response using ChatSession method
        rag_response = ChatSession.get_chat_response(
            session_id=session_id,
            user_message=message_content
        )
        
        response_text = rag_response.get('response', 'I apologize, but I encountered an error. Please try again.')
        
        # Add assistant message to session
        BotSessionManager.add_message_to_session(
            session_id=session_id,
            role='assistant',
            content=response_text
        )
        
        # Format response for WhatsApp
        formatted_response = message_formatter.format_for_whatsapp(response_text)
        
        # Extract buttons from response (if any)
        cleaned_text, buttons = message_formatter.extract_buttons_from_text(formatted_response)
        
        # Check if message needs to be split
        message_chunks = message_formatter.truncate_message(
            cleaned_text,
            max_length=4000,
            platform='whatsapp'
        )
        
        # Send response(s)
        if len(buttons) > 0:
            # Decide between buttons or list
            use_buttons, formatted_options = sender.create_button_list_from_options(buttons)
            
            if use_buttons:
                # Use quick reply buttons (max 3)
                await sender.send_text_with_buttons(
                    to_number=from_number,
                    message=message_chunks[0],
                    buttons=formatted_options
                )
            else:
                # Use list menu (4+ options)
                await sender.send_list_message(
                    to_number=from_number,
                    message=message_chunks[0],
                    button_text="Choose Option",
                    sections=formatted_options
                )
            
            # Send remaining chunks as plain text
            for chunk in message_chunks[1:]:
                await asyncio.sleep(0.5)  # Small delay between messages
                await sender.send_text_message(from_number, chunk)
        else:
            # No buttons - send as plain text
            for chunk in message_chunks:
                await sender.send_text_message(from_number, chunk)
                if len(message_chunks) > 1:
                    await asyncio.sleep(0.5)  # Small delay between chunks
        
        # Update session activity
        BotSessionManager.update_session_activity(session_id)
        
        logger.info(f"Successfully processed message for {from_number}")
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}", exc_info=True)
        
        # Send error message to user
        if sender and message_data:
            try:
                error_msg = message_formatter.format_error_message('whatsapp', 'general')
                await sender.send_text_message(
                    message_data.get("from_number", "").replace("+", ""),
                    error_msg
                )
            except:
                logger.error("Failed to send error message to user")


@whatsapp_bp.route('/test', methods=['POST'])
def test_send_message():
    """
    Test endpoint to send a message
    Use this for testing without webhook
    
    POST /api/whatsapp/test
    {
        "to": "+919876543210",
        "message": "Hello from the bot!"
    }
    """
    try:
        data = request.get_json()
        to_number = data.get('to')
        message = data.get('message')
        
        if not to_number or not message:
            return jsonify({"error": "Missing 'to' or 'message' field"}), 400
        
        # Initialize sender
        sender = WhatsAppMessageSender(
            access_token=Config.WHATSAPP_ACCESS_TOKEN,
            phone_number_id=Config.WHATSAPP_PHONE_NUMBER_ID
        )
        
        # Send message
        result = asyncio.run(sender.send_text_message(to_number, message))
        
        if result:
            return jsonify({
                "status": "success",
                "message_id": result.get('messages', [{}])[0].get('id')
            }), 200
        else:
            return jsonify({"status": "failed"}), 500
            
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@whatsapp_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        "status": "healthy",
        "service": "whatsapp",
        "configured": bool(Config.WHATSAPP_ACCESS_TOKEN and Config.WHATSAPP_PHONE_NUMBER_ID)
    }), 200