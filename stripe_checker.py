from pyrogram import Client, filters, enums
import re
import time
import stripe

# API
api_id = "YOUR_API_ID_HERE"
api_hash = "YOUR_API_HASH_HERE"
bot_token = 'YOUR_BOT_TOKEN_HERE'
stripe.api_key = 'YOUR_API_KEY_HERE'

# Initialize bot
app = Client("cardcheckbot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

pending_users = {}

# Function to convert country code to flag emoji
def country_to_flag(country_code):
    # Convert the 2-letter country code to a flag emoji
    return ''.join(chr(127397 + ord(c)) for c in country_code.upper())

# Function to validate card details with Stripe API
def validate_card(card_number, exp_month, exp_year, cvc):
    try:
        start_time = time.time()
        payment_method = stripe.PaymentMethod.create(
            type='card', card={'number': card_number, 'exp_month': exp_month, 'exp_year': exp_year, 'cvc': cvc}
        )
        country_code = payment_method.card.country
        flag = country_to_flag(country_code)

        return {
            'card': f"{card_number}|{exp_month}|{exp_year}|{cvc}",
            'issuer': payment_method.card.issuer,
            'gateway': payment_method.card.brand,
            'info': payment_method.card.checks.cvc_check,
            'country': f"{flag} {country_code}",
            'response_time': round(time.time() - start_time, 2),
            'response': 'Approved ✅'
        }
    except stripe.error.CardError:
        return {
            'card': f"{card_number}|{exp_month}|{exp_year}|{cvc}",
            'response': 'Declined ❌',
            'issuer': 'JPMORGAN CHASE BANK N.A. - DEBIT',
            'country': '🇺🇸 UNITED STATES',
            'info': 'Call Issuer. Pick Up Card.',
            'gateway': 'Braintree Auth',
            'response_time': round(time.time() - start_time, 2)
        }
    except Exception as e:
        return {'error': str(e)}

# Command handler for '/chk'
@app.on_message(filters.command("chk"))
async def handle_chk(client, message):
    user_id = message.from_user.id
    if len(message.command) == 1:
        pending_users[user_id] = True
        await message.reply_text("🔍 Provide card details in format: ××××××××××××××××|MM|YY|CVC")
    else:
        await process_cards(message, message.text.split(maxsplit=1)[1])

# Handler for private messages
@app.on_message(filters.text & filters.private)
async def handle_responses(client, message):
    user_id = message.from_user.id
    if user_id in pending_users:
        del pending_users[user_id]
        await process_cards(message, message.text)

# Function to process multiple cards
async def process_cards(message, card_input):
    try:
        card_entries = re.split(r'\s+', card_input.strip())
        if not card_entries:
            await message.reply_text("⚠️ No valid card details provided.")
            return

        processing_message = await message.reply_text("🔍 Processing...")
        results = ""

        # Process each card entry
        for card_entry in card_entries:
            match = re.match(r"(\d{16})\|(\d{2})\|(\d{2}|\d{4})\|(\d{3})", card_entry) or \
                    re.match(r"(\d{16})\|(\d{2})/(\d{2}|\d{4})\|(\d{3})", card_entry) or \
                    re.match(r"(\d{16})\|(\d{2})\|(\d{2})\|(\d{3})", card_entry)

            if match:
                card_number, exp_month, exp_year, cvc = match.groups()
                if len(exp_year) == 2:
                    exp_year = "20" + exp_year

                result = validate_card(card_number, int(exp_month), int(exp_year), cvc)
                if 'error' in result:
                    results += f"⚠️ Error with card {card_number}: {result['error']}\n\n"
                else:
                    results += f"""
𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ✅

𝗖𝗮𝗿𝗱: {result['card']}
𝐆𝐚𝐭𝐞𝐰𝐚𝐲: {result['gateway']}
𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: {result['response']}

𝗜𝗻𝗳𝗼: {result['info']}
𝐈𝐬𝐬𝐮𝐞𝐫: {result['issuer']}
𝐂𝐨𝐮𝐧𝐭𝐫𝐲: {result['country']}

𝗧𝗶𝗺𝗲: {result['response_time']} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬
                    """ if result['response'] == 'Approved ✅' else f"""
𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝 ❌

𝗖𝗮𝗿𝗱: {result['card']}
𝐆𝐚𝐭𝐞𝐰𝐚𝐲: {result['gateway']}
𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞: {result['info']}

𝗜𝗻𝗳𝗼: {result['info']}
𝐈𝐬𝐬𝐮𝐞𝐫: {result['issuer']}
𝐂𝐨𝐮𝐧𝐭𝐫𝐲: {result['country']}

𝗧𝗶𝗺𝗲: {result['response_time']} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬
                    """
            else:
                results += f"⚠️ Invalid card format: {card_entry}\n\n"        
        if results:
            await processing_message.edit_text(results.strip(), parse_mode=enums.ParseMode.HTML)
        else:
            await processing_message.edit_text("⚠️ No valid cards processed.", parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        await message.reply_text(f"⚠️ An error occurred: {str(e)}", parse_mode=enums.ParseMode.HTML)

# Start the bot
print("Bot is running...")
app.run()
