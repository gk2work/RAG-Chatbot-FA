"""
Quick test script for Telegram bot using polling (no webhook needed)
Run this for local testing without ngrok
"""

import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# IMPORTANT: Initialize database BEFORE importing handlers
from app.models import init_db
print("Initializing database connection...")
init_db()
print("✅ Database initialized")

# Now import after DB is initialized
from app.config import Config
from app.integrations.telegram.webhook_handler import TelegramWebhookHandler

webhook_handler = TelegramWebhookHandler()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    # Convert Telegram update to webhook format
    update_data = update.to_dict()
    
    # Process with your webhook handler
    response_data = webhook_handler.process_update(update_data)
    
    if response_data.get('success'):
        chat_id = response_data.get('chat_id')
        text = response_data.get('text')
        reply_markup = response_data.get('reply_markup')
        
        if chat_id and text:
            if reply_markup:
                from telegram import InlineKeyboardMarkup
                keyboard = InlineKeyboardMarkup(reply_markup['inline_keyboard'])
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    update_data = update.to_dict()
    response_data = webhook_handler.process_update(update_data)
    
    # Answer callback query
    await update.callback_query.answer()
    
    if response_data.get('success'):
        chat_id = response_data.get('chat_id')
        text = response_data.get('text')
        reply_markup = response_data.get('reply_markup')
        
        if chat_id and text:
            if reply_markup:
                from telegram import InlineKeyboardMarkup
                keyboard = InlineKeyboardMarkup(reply_markup['inline_keyboard'])
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')

def main():
    """Run the bot in polling mode"""
    print("\n" + "="*60)
    print("🤖 Starting Telegram bot in POLLING mode")
    print("="*60)
    print(f"✅ Bot token configured: {bool(Config.TELEGRAM_BOT_TOKEN)}")
    print(f"✅ Database connected: {bool(Config.MONGODB_URI)}")
    print(f"✅ Default university: {Config.DEFAULT_UNIVERSITY_X_ID}")
    print("="*60)
    
    # Create application
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("start", handle_message))
    application.add_handler(CommandHandler("help", handle_message))
    application.add_handler(CommandHandler("programs", handle_message))
    application.add_handler(CommandHandler("status", handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    print("\n✅ Bot is running! Open Telegram and message @fa_uni_bot")
    print("💬 Send /start to begin")
    print("⏹️  Press Ctrl+C to stop\n")
    
    # Run polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()