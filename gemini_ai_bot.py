import logging
import asyncio
from google import genai
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# --- CONFIGURATION (Replace these) ---
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
GEMINI_API_KEY = "YOUR_PAID_GEMINI_API_KEY"
YOUR_TELEGRAM_USER_ID = 123456789  # Replace with your numeric ID to lock the bot
MODEL_NAME = "gemini-2.0-pro-exp"

# Initialize Gemini
client = genai.Client(api_key=GEMINI_API_KEY)
user_sessions = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # 🔐 Security Lock: Only you can use this paid bot
    if user_id != YOUR_TELEGRAM_USER_ID:
        await update.message.reply_text("🚫 Access Denied. This is a private bot.")
        return

    user_text = update.message.text
    if user_id not in user_sessions:
        user_sessions[user_id] = []

    # Add message to history
    user_sessions[user_id].append({"role": "user", "parts": [{"text": user_text}]})

    try:
        # Show "typing..." status
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)

        # Call Gemini API
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_sessions[user_id]
        )

        bot_response = response.text
        user_sessions[user_id].append({"role": "model", "parts": [{"text": bot_response}]})

        # Memory limit: Keep last 20 messages to balance context vs cost
        if len(user_sessions[user_id]) > 20:
            user_sessions[user_id] = user_sessions[user_id][-20:]

        await update.message.reply_text(bot_response)

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("⚠️ Something went wrong. Check VPS logs.")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == YOUR_TELEGRAM_USER_ID:
        user_sessions[update.effective_user.id] = []
        await update.message.reply_text("🧹 Memory cleared! Fresh start.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_chat))
    
    print("🚀 Premium Bot is live on VPS. Chat away!")
    app.run_polling()
