from pyrogram import Client, filters
from twilio.rest import Client as TwilioClient
import re

# Telegram bot credentials
api_id = "YOUR_API_ID"
api_hash = "YOUR_API_HASH"
bot_token = 'YOUR_BOT_TOKEN'

# Twilio credentials
account_sid = "YOUR_ACCOUNT_SID"
auth_token = "YOUR_AUTH_TOKEN"
twilio_phone_number = "YOUR_TWILIO_PHONE_NUMBER"

# Initialize bots
app = Client("smsbot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
twilio_client = TwilioClient(account_sid, auth_token)

# Store user session data
user_sessions = {}

# Function to validate phone number using Twilio's Lookup API
def validate_phone_number(phone):
    try:
        lookup = twilio_client.lookups.v1.phone_numbers(phone).fetch()
        return True
    except Exception as e:
        return False

# Function to check if the phone number is in E.164 format
def is_valid_phone_number(phone):
    return bool(re.match(r"^\+[1-9]\d{1,14}$", phone))

@app.on_message(filters.command("sms"))
async def handle_sms_command(client, message):
    user_id = message.from_user.id
    user_sessions[user_id] = {}
    await message.reply_text("📲 Please enter the recipient's phone number with country code (e.g., +919876543210).")

@app.on_message(filters.text & filters.private)
async def handle_input(client, message):
    user_id = message.from_user.id
    if user_id not in user_sessions:
        return

    session = user_sessions[user_id]
    if "phone" not in session:
        phone = message.text.strip()
        if not is_valid_phone_number(phone):
            await message.reply_text("❌ Please enter a valid phone number in E.164 format (e.g., +919876543210).")
            return
        session["phone"] = phone
        await message.reply_text("✉️ Enter the message you want to send.")
    elif "message" not in session:
        session["message"] = message.text.strip()
        phone = session["phone"]
        body = session["message"]

        # Validate phone number before sending the message
        if not validate_phone_number(phone):
            await message.reply_text("❌ Invalid phone number. Please try again with a valid number.")
            user_sessions.pop(user_id, None)
            return

        try:
            twilio_message = twilio_client.messages.create(
                from_=twilio_phone_number, body=body, to=phone
            )
            await message.reply_text("✅ Message sent successfully!")
        except Exception as e:
            await message.reply_text(f"❌ Failed to send message. Error: {e}")
        user_sessions.pop(user_id, None)

print("Bot is running...")
app.run()
